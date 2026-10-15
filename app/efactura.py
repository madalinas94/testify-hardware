"""Import e-Factura: facturile primite de la furnizori, descărcate din SPV (XML UBL 2.1, RO_CIUS).

Fiecare linie de pe factură devine fie o recepție de marfă (dacă produsul se potrivește cu unul din
stoc), fie o cheltuială (cu o categorie propusă). Mai întâi se face o previzualizare, pe care
proprietarul o poate corecta, apoi se salvează. Aceeași factură nu se importă de două ori.
"""

import difflib
import io
import re
import unicodedata
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}
# Cuvinte din descrierea liniei → categoria de cheltuială propusă.
KEYWORDS = [
    (("chirie", "inchiriere"), "Chirie"),
    (("energie", "electric", "gaz", "apa ", "canal", "salubr"), "Utilități"),
    (("internet", "telefon", "abonament mobil", "fibra"), "Internet și telefonie"),
    (("curier", "transport", "livrare", "fan courier", "sameday", "cargus"), "Transport"),
    (("motorina", "benzina", "carburant", "combustibil", "diesel", "spalatorie", "rovinieta"), "Combustibil și auto"),
    (("contabil", "audit"), "Contabilitate"),
    (("reclama", "publicitate", "marketing", "google ads", "facebook", "meta "), "Marketing"),
    (("licenta", "software", "saas", "hosting", "domeniu", "cloud", "microsoft 365"), "Software și abonamente"),
    (("laptop", "monitor", "imprimanta", "birou", "scaun", "mobilier"), "Echipamente IT și mobilier"),
    (("comision", "pos", "bancar"), "Comisioane bancare și POS"),
    (("asigurare", "rca", "casco", "polita"), "Asigurări"),
    (("reparatie", "mentenanta", "service"), "Mentenanță și reparații"),
    (("ambalaj", "cutii", "folie", "banda adeziva", "hartie", "consumabil", "toner"), "Ambalaje și consumabile"),
    (("medicina muncii", "ssm", "psi"), "Medicina muncii și SSM"),
    (("curs", "training", "instruire"), "Training și cursuri"),
    (("protocol", "cazare", "hotel", "restaurant", "deplasare"), "Protocol și deplasări"),
]


class EFacturaError(ValueError):
    pass


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text)).strip()


def xml_documents(filename: str, content: bytes) -> list[tuple[str, bytes]]:
    """Un XML, sau arhiva ZIP din SPV (factura + semnătura; semnătura se ignoră)."""
    if filename.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                return [(name, archive.read(name)) for name in archive.namelist()
                        if name.lower().endswith(".xml") and "semnatura" not in name.lower()]
        except zipfile.BadZipFile:
            raise EFacturaError(f"„{filename}” nu este o arhivă ZIP validă.") from None
    return [(filename, content)]


def text(node, path: str, default: str = "") -> str:
    found = node.find(path, NS)
    return found.text.strip() if found is not None and found.text else default


def number(node, path: str) -> float:
    value = text(node, path, "0")
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_invoice(filename: str, content: bytes) -> dict:
    if b"<!DOCTYPE" in content[:2000] or b"<!ENTITY" in content[:4000]:
        raise EFacturaError(f"„{filename}” conține construcții XML nepermise.")
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        raise EFacturaError(f"„{filename}” nu este un XML valid.") from None
    kind = root.tag.split("}")[-1]
    if kind not in ("Invoice", "CreditNote"):
        raise EFacturaError(f"„{filename}” nu este o e-Factură (Invoice sau CreditNote).")
    sign = -1 if kind == "CreditNote" or text(root, "cbc:InvoiceTypeCode") == "381" else 1
    supplier = root.find("cac:AccountingSupplierParty/cac:Party", NS)
    if supplier is None:
        raise EFacturaError(f"„{filename}”: lipsește furnizorul.")
    name = (text(supplier, "cac:PartyLegalEntity/cbc:RegistrationName")
            or text(supplier, "cac:PartyName/cbc:Name") or "Furnizor necunoscut")
    vat_id = text(supplier, "cac:PartyTaxScheme/cbc:CompanyID") or text(supplier, "cac:PartyLegalEntity/cbc:CompanyID")
    issue = text(root, "cbc:IssueDate")
    try:
        date.fromisoformat(issue)
    except ValueError:
        raise EFacturaError(f"„{filename}”: data facturii lipsește sau nu e corectă.") from None
    due = text(root, "cbc:DueDate") or text(root, "cac:PaymentMeans/cbc:PaymentDueDate")
    lines = []
    line_tag = "cac:CreditNoteLine" if kind == "CreditNote" else "cac:InvoiceLine"
    qty_tag = "cbc:CreditedQuantity" if kind == "CreditNote" else "cbc:InvoicedQuantity"
    for index, line in enumerate(root.findall(line_tag, NS)):
        quantity = number(line, qty_tag) or 1
        net = number(line, "cbc:LineExtensionAmount")
        lines.append({
            "index": index,
            "name": text(line, "cac:Item/cbc:Name") or text(line, "cac:Item/cbc:Description") or "Produs",
            "code": text(line, "cac:Item/cac:SellersItemIdentification/cbc:ID"),
            "quantity": quantity,
            "unit_price": round(net / quantity, 4) if quantity else net,
            "net": round(sign * net, 2),
            "vat_rate": number(line, "cac:Item/cac:ClassifiedTaxCategory/cbc:Percent"),
        })
    if not lines:
        raise EFacturaError(f"„{filename}”: factura nu are linii.")
    return {
        "file": filename, "kind": kind, "credit_note": sign < 0,
        "number": text(root, "cbc:ID"), "date": issue, "due_date": due or None,
        "supplier": name, "supplier_vat_id": vat_id,
        "net": round(sign * number(root, "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount"), 2),
        "vat": round(sign * number(root, "cac:TaxTotal/cbc:TaxAmount"), 2),
        "total": round(sign * number(root, "cac:LegalMonetaryTotal/cbc:PayableAmount"), 2),
        "lines": lines,
    }


def vat_kind(rate: float) -> str:
    if rate <= 0:
        return "none"
    return "reduced" if rate < 15 else "standard"


def match_product(line: dict, products: list[dict], supplier: str) -> dict | None:
    """Produsul din stoc: după cod, apoi după nume (de preferat de la același furnizor)."""
    if line["code"]:
        for product in products:
            if norm(product["code"]) == norm(line["code"]):
                return product
    target = norm(line["name"])
    best, best_score = None, 0.0
    for product in products:
        score = difflib.SequenceMatcher(None, target, norm(product["name"])).ratio()
        if norm(product["supplier"]) == norm(supplier):
            score += 0.05
        if score > best_score:
            best, best_score = product, score
    return best if best_score >= 0.82 else None


def guess_category(conn, line_name: str, supplier: str) -> str:
    row = conn.execute("SELECT category FROM expenses WHERE supplier = ? GROUP BY category "
                       "ORDER BY COUNT(*) DESC LIMIT 1", (supplier,)).fetchone()
    if row:
        return row["category"]
    words = f" {norm(line_name)} {norm(supplier)} "
    for keys, category in KEYWORDS:
        if any(key in words for key in keys):
            return category
    return "Altele"


def already_imported(conn, supplier: str, number: str) -> bool:
    if not number:
        return False
    return bool(conn.execute(
        "SELECT 1 FROM purchases WHERE supplier = ? AND doc_number = ? UNION ALL "
        "SELECT 1 FROM expenses WHERE supplier = ? AND doc_number = ?", (supplier, number, supplier, number)
    ).fetchone())


def preview(conn, files: list[tuple[str, bytes]]) -> dict:
    products = [dict(row) for row in conn.execute("SELECT id, code, name, supplier, cost FROM products")]
    invoices, errors = [], []
    for filename, content in files:
        try:
            documents = xml_documents(filename, content)
        except EFacturaError as error:
            errors.append(str(error))
            continue
        for name, data in documents:
            try:
                invoice = parse_invoice(name, data)
            except EFacturaError as error:
                errors.append(str(error))
                continue
            invoice["duplicate"] = already_imported(conn, invoice["supplier"], invoice["number"])
            for line in invoice["lines"]:
                product = None if invoice["credit_note"] else match_product(line, products, invoice["supplier"])
                whole = float(line["quantity"]).is_integer()
                if product and whole:
                    line.update(target="product", product_id=product["id"], product_name=product["name"])
                else:
                    line.update(target="expense", product_id=None,
                                category=guess_category(conn, line["name"], invoice["supplier"]))
                line["vat_kind"] = vat_kind(line["vat_rate"])
            invoices.append(invoice)
    if not invoices and errors:
        raise EFacturaError(" ".join(errors))
    return {"invoices": invoices, "errors": errors}


def save(conn, invoices: list[dict], supplier_terms) -> dict:
    """Salvează facturile confirmate. supplier_terms(conn, nume) dă termenul de plată."""
    counts = {"purchases": 0, "expenses": 0, "skipped": 0}
    for invoice in invoices:
        if already_imported(conn, invoice["supplier"], invoice["number"]):
            counts["skipped"] += 1
            continue
        terms = supplier_terms(conn, invoice["supplier"])
        due = invoice.get("due_date") or (date.fromisoformat(invoice["date"]) + timedelta(days=terms)).isoformat()
        paid = int(due <= invoice["date"])
        for line in invoice["lines"]:
            if line.get("target") == "skip":
                continue
            if line.get("target") == "product" and line.get("product_id"):
                quantity = int(round(line["quantity"]))
                if quantity <= 0:
                    raise EFacturaError(f"Factura {invoice['number']}: cantitatea pentru „{line['name']}” "
                                        "trebuie să fie pozitivă.")
                unit_cost = round(line["net"] / quantity, 4)
                conn.execute("INSERT INTO purchases(date, doc_number, supplier, product_id, quantity, unit_cost, "
                             "due_date, paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (invoice["date"], invoice["number"], invoice["supplier"], line["product_id"], quantity,
                              unit_cost, due, paid))
                conn.execute("UPDATE products SET cost = ? WHERE id = ?", (unit_cost, line["product_id"]))
                counts["purchases"] += 1
            else:
                category = line.get("category") or "Altele"
                if not conn.execute("SELECT 1 FROM categories WHERE name = ?", (category,)).fetchone():
                    raise EFacturaError(f"Categoria „{category}” nu există.")
                conn.execute("INSERT INTO expenses(date, category, description, amount, supplier, vat_kind, doc_number) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (invoice["date"], category, line["name"][:200], line["net"], invoice["supplier"],
                              line.get("vat_kind") or vat_kind(line["vat_rate"]), invoice["number"]))
                counts["expenses"] += 1
    return counts
