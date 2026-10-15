# Testify Hardware — aplicația internă pentru calculul lunar

[![Teste](https://github.com/madalinas94/testify-hardware/actions/workflows/tests.yml/badge.svg)](https://github.com/madalinas94/testify-hardware/actions/workflows/tests.yml)
[![Program Windows](https://github.com/madalinas94/testify-hardware/actions/workflows/windows-exe.yml/badge.svg)](https://github.com/madalinas94/testify-hardware/actions/workflows/windows-exe.yml)

Aplicație web care rulează pe calculatorul de la birou și înlocuiește fișierele Excel.
Îi arată proprietarului, „la un click distanță”, câți bani intră, unde se duc, ce taxe
plătește firma și cât îi rămâne lui. Cotele de taxe se actualizează automat când se
schimbă Codul fiscal.

## Cum o deschideți (pe scurt)

Ghidul de folosire, pe o pagină: [GHID-ROBERT.md](GHID-ROBERT.md).


**Varianta cea mai simplă (Windows, fără Python):** în tabul **Actions → Program Windows (.exe)**,
deschideți ultima rulare verde și descărcați **TestifyHardware-Windows** (sau, dacă există, arhiva
din **Releases**). Dezarhivați, dublu-click pe `TestifyHardware.exe` și aplicația se deschide în
browser. Datele stau în folderul `TestifyData`, lângă program. Windows poate afișa „Windows protected
your PC”, pentru că programul nu e semnat digital: apăsați **More info → Run anyway**.

**Varianta cu Python** (Windows, Mac, Linux):

1. **Instalați Python** (gratuit) de pe <https://www.python.org/downloads/>. Pe Windows, la
   instalare bifați **„Add python.exe to PATH”**.
2. **Descărcați aplicația:** pe această pagină, butonul verde **Code → Download ZIP**, apoi
   dezarhivați folderul (sau `git clone` dacă folosiți Git).
3. **Porniți-o:** pe Windows, dublu-click pe **`start.bat`**; pe Mac/Linux, rulați `./start.sh`
   în terminal. Prima pornire durează un minut (instalează ce îi trebuie).
4. Aplicația se deschide în browser la <http://localhost:8000>. La prima intrare alegeți parola,
   notați codul de recuperare și bifați „Încarcă datele firmei” ca să vedeți datele din T3 2026.
5. **Opțional, Testi cu AI:** Setări → Testi cu inteligență artificială → lipiți cheia API
   Anthropic primită separat (cheia nu se pune niciodată în acest repository).

## Ce știe să facă

| Pagină | Ce conține |
| --- | --- |
| **Dashboard** | Venituri, costuri, profit și „cât îți rămâne ție” pe lună, cu comparație față de luna trecută; evoluția pe 12 luni; graficul „Unde se duc banii”; observații automate; top produse |
| **Vânzări** | Facturi pe produse din stoc (preț și cost se completează singure, numărul facturii e automat) sau doar totalul pe zi/lună; client, scadență și status încasat/neîncasat |
| **Stoc** | Produse cu cod, furnizor, preț, cost, stoc minim; stocul scade la vânzare și crește la recepția de marfă (NIR); alerte de stoc minim, „se termină în ~X zile”, fișa de inventar lunară |
| **Clienți** | Clienți B2B/B2C/marketplace cu termen de plată, vânzări pe client, facturi de încasat și restanțe |
| **Furnizori** | Furnizori cu termen de plată (implicit 30 de zile), marfă cumpărată, plăți de făcut în ordinea scadenței, restanțe și ce e scadent în 7 zile |
| **Trezorerie** | Câți bani vor fi în cont în următoarele 30 de zile: soldul de azi + încasări la scadență + vânzări pe loc − furnizori − cheltuieli − salarii − taxe; grafic zi de zi și avertizare dacă soldul ar ajunge pe minus |
| **Cheltuieli** | 19 categorii implicite, editabile: marfă, chirie, utilități, internet și telefonie, transport, combustibil, contabilitate, marketing, software, echipamente, comisioane bancare/POS, asigurări, reparații, ambalaje, taxe locale, SSM, training, protocol, altele |
| **Angajați** | Adăugare angajați, salariu brut cu istoric de măriri, calcul automat al netului și al costului pentru firmă, stat de plată lunar cu zile lucrătoare (sărbătorile legale incluse), concedii de odihnă/medicale/fără plată, zile de concediu rămase, normă parțială și avertizare sub salariul minim |
| **Taxe** | Decontul de TVA (colectată − deductibilă = de plată), CAS, CASS, impozit pe venit, CAM și impozitul pe profit, explicate pe înțeles, cu cotele valabile în luna aleasă |
| **Decizii** | **Simulatorul „Ce-ar fi dacă…”**: cursoare pentru prețuri, cantități, prețurile furnizorilor, măriri, angajați noi și cheltuieli în plus; profitul, impozitul, pragul de rentabilitate și „cât îți rămâne” se recalculează pe loc. **Analiza clienților și produselor**: cine aduce 80% din profit (clase A/B/C), clienți fideli care nu mai cumpără, marfă care stă și blochează bani |
| **Calendar fiscal** | Termenele ANAF cu sume: D112 (salarii), D300 (TVA), D394, impozitul pe profit trimestrial și D101; termenele din weekend/sărbători mutate automat; bifă „Am plătit”; Testi amintește cu 7 zile înainte |
| **Rapoarte** | Contul de profit și pierdere în structura raportului contabil, indicatori de control, export Excel (cu foi pentru vânzări, achiziții, cheltuieli, stocuri, salarii) și PDF; **închiderea lunii** (cu listă de verificări) și **jurnalul de modificări** |
| **Setări** | Firma, proprietarul, regimul de impozitare, plătitor de TVA, ziua salariilor, pierderea fiscală de recuperat, legislația fiscală (cu istoric), import din Excel/CSV, parola, **copii de siguranță** |

În plus:

- **Testi, asistentul:** un robot animat care îl salută pe proprietar la intrare, îi spune pe
  scurt cum a mers luna, îl avertizează când o cheltuială crește prea repede și îi explică
  noutățile fiscale în limbaj simplu.
- **Testi cu AI (opțional):** din **Setări → Testi cu inteligență artificială**, cu o cheie API
  Anthropic, Robert poate pune întrebări libere („De ce a scăzut profitul în august?”, „Ce produse
  să comand?”). Răspunsurile vin de la modelul Claude (`claude-opus-5-5`), pe baza unui rezumat al
  datelor firmei trimis la fiecare întrebare. Fără cheie, opțiunea nu apare și aplicația rămâne
  complet locală. Vedeți secțiunea „Asistentul AI” de mai jos.
- **Poză la bon:** la Cheltuieli, „Citește bonul”: fotografiați bonul sau factura (sau alegeți un PDF), iar
  Testi (cu AI) citește furnizorul, data, suma, TVA și propune categoria. Robert verifică și salvează.
- **Import e-Factura (SPV):** din Setări, fișierele XML sau arhivele ZIP descărcate din Spațiul Privat
  Virtual ANAF. Liniile cu marfă devin recepții în stoc (produsul se recunoaște după cod sau nume), restul
  devin cheltuieli cu categoria propusă. Notele de credit scad cheltuielile. Aceeași factură nu intră de două ori.
- **Comenzi recomandate:** la Stoc, ce trebuie comandat, cât, de la cine și până când, după ritmul
  vânzărilor, termenul de livrare al furnizorului și banii din cont; comanda se copiază pentru email/WhatsApp.
- **Scrisoarea lunii:** la Rapoarte, un PDF cu grafice și explicații pe înțeles (ce a mers bine, la ce să
  fii atent, ce urmează), bun de trimis partenerilor sau băncii.
- **Testi vorbește:** butonul cu difuzor din fereastra lui Testi citește mesajele cu voce, în română.
- **Siguranță:** blocare automată după 15 minute fără activitate (configurabil), PIN de intrare rapidă pe
  telefon (după 3 greșeli se cere parola) și o copie zilnică în plus într-un folder ales (de exemplu
  sincronizat cu Google Drive / OneDrive).
- **Retururi și reduceri:** la vânzări, butonul de retur emite o factură de stornare (cu minus),
  totală sau parțială, legată de factura inițială; marfa revine în stoc, iar venitul, TVA și
  profitul scad. Facturile pe produse pot avea reducere în procente.
- **Obiective lunare:** vânzări și profit țintă (în fiecare lună sau doar pentru o lună anume);
  dashboard-ul arată cât s-a atins și unde se ajunge la final de lună, în ritmul de până acum.
- **Copii de siguranță:** automat în fiecare zi (se păstrează ultimele 30), la închiderea lunii și
  înainte de orice restaurare; **export complet** (ZIP cu baza de date și toate datele în Excel) din
  care se poate restaura totul, de exemplu pe alt calculator.
- **Închiderea lunii:** după trimiterea raportului la contabil, luna se închide și nimic din ea nu
  mai poate fi modificat (nici din import); se poate redeschide, iar totul apare în jurnal.
- **Jurnal de modificări:** fiecare adăugare, modificare sau ștergere, cu valoarea veche și cea nouă.
- **Adăugare rapidă:** butonul „+ Adaugă” din colț, pentru o vânzare sau o cheltuială din câteva atingeri.
- **Versiune de telefon:** interfața se adaptează la ecranul mic, are meniu jos și se poate
  instala ca aplicație (vezi mai jos).

Cerințele clientului, pe scurt: un singur utilizator (proprietarul, Robert) protejat cu parolă,
impozit pe profit (nu e microîntreprindere), salarii stabilite la brut, doar vânzare de
accesorii, produse și inventar în aplicație, rulare pe calculatorul de la birou, separat de
site-ul firmei, cu acces de pe telefon.

**TVA:** clientul a spus inițial că nu plătește TVA, dar raportul contabilului calculează TVA
lunar (21%), iar la o cifră de afaceri de ~1,7 milioane lei pe an înregistrarea în scopuri de TVA
este obligatorie. Aplicația urmează raportul contabil (plătitor de TVA); setarea se poate
schimba din **Setări**.

## Datele firmei și verificarea cu contabilul

În `sample_data/` sunt fișierele primite de la firmă: raportul contabil pe T3 2026 (iulie–
septembrie), produsele, clienții, angajații, vânzările, cheltuielile și inventarul pe
septembrie. La prima pornire (sau din Setări) aplicația le poate încărca automat.

Calculele aplicației dau **exact aceleași cifre ca raportul contabilului** pentru fiecare lună:
venituri, costul mărfii vândute, marja brută, cheltuieli, profit, impozit pe profit, TVA de plată,
valoarea stocului, salarii și creanțe. Testele din `tests/test_client_data.py` verifică asta
automat. Pentru asta, aplicația folosește aceleași reguli ca statul de plată și raportul:
contribuțiile și impozitele se rotunjesc la leu (0,5 în sus), iar TVA se calculează pe fiecare document.

**Import:** din **Setări → Import din Excel / CSV** se pot aduce oricând fișiere noi. Tabelele
sunt recunoscute după coloane, iar ce există deja (aceeași factură, același NIR) nu se dublează.

## Pornire

Necesită Python 3.10 sau mai nou.

- **Windows:** dublu-click pe `start.bat`. Prima dată instalează tot ce trebuie, apoi deschide
  aplicația în browser.
- **macOS / Linux:** `./start.sh`, apoi deschideți <http://localhost:8000>.

La prima pornire alegeți parola și primiți un **cod de recuperare** (de forma `ABCD-EFGH-JKMN-PQRS`),
pe care îl notați pe hârtie, îl salvați ca fișier sau îl printați. Dacă uitați parola, pe ecranul de
intrare apăsați „Am uitat parola”, introduceți codul și alegeți o parolă nouă; codul folosit expiră și
primiți automat unul nou. Din **Setări** se poate genera oricând un cod nou (cu parola actuală).
După 5 încercări greșite la rând, intrarea se blochează 5 minute. Dacă bifați „Încarcă datele firmei”, aplicația se umple cu
datele din T3 2026 primite de la firmă.

**De pe telefon:** cu telefonul conectat la Wi-Fi-ul de la birou, deschideți
`http://<adresa-IP-a-calculatorului>:8000` (adresa IP o vedeți cu `ipconfig` pe Windows), apoi
din meniul browserului alegeți „Adaugă pe ecranul principal”. Instalarea completă ca aplicație
(cu funcționare offline) cere o adresă HTTPS; pe calculatorul local (`localhost`) merge direct.

Datele se salvează în `data/testify.db` (la programul Windows, în `TestifyData`). Aplicația face
singură o copie în fiecare zi în `data/backups`; din **Setări → Copii de siguranță** se poate
descărca exportul complet, de păstrat pe un stick sau în cloud.

## Actualizarea automată a regulilor fiscale

Cotele de taxe nu sunt scrise în cod. Ele stau în fișierul `app/fiscal/ro.json`, în care
fiecare set de cote are **data de la care se aplică**:

- Aplicația descarcă singură versiunea publicată a acestui fișier, la pornire și apoi la fiecare
  6 ore. Adresa implicită este fișierul `app/fiscal/ro.json` din repository-ul
  `madalinas94/testify-hardware`, de pe ramura `main`; se poate
  schimba cu variabila de mediu `TESTIFY_FISCAL_FEED` (un șir gol oprește actualizarea).
- Când apare o regulă nouă, aplicația o salvează, recalculează lunile la care se aplică, iar
  Testi îl anunță pe proprietar ce s-a schimbat. O regulă poate fi publicată înainte să intre în
  vigoare (de exemplu în decembrie, pentru 1 ianuarie).
- Lunile trecute rămân calculate cu cotele valabile atunci (de exemplu, dividendele din 2025 cu
  10%, cele din 2026 cu 16%).
- Dacă nu există internet sau fișierul descărcat e invalid, aplicația păstrează ultimele reguli
  salvate și nu strică niciun calcul.

**Cine actualizează fișierul:** statul nu publică cotele într-un format pe care un program să-l
poată citi automat, iar textul legii nu poate fi interpretat automat în siguranță. De aceea,
când se schimbă legea, cine întreține aplicația adaugă o regulă nouă în `ro.json` și o publică.
De acolo, toate instalările se actualizează singure. Programele de facturare din România
funcționează la fel.

## Asistentul AI (opțional)

- **Pornire:** Setări → bifați „Activează asistentul AI” și lipiți cheia API Anthropic (din
  console.anthropic.com). Cheia se poate da și prin variabila de mediu `ANTHROPIC_API_KEY`.
- **Ce se trimite:** la fiecare întrebare, un rezumat JSON cu lunile (venituri, costuri, profit,
  TVA), stocul, clienții, furnizorii, angajații și salariile, plus ultimele mesaje din conversație.
  Parola, codul de recuperare și cheia API nu se trimit niciodată.
- **Cost și internet:** fiecare întrebare consumă din contul Anthropic (rezumatul are ~3.000 de
  tokeni) și cere conexiune la internet. Instrucțiunile fixe sunt marcate pentru cache, ca să coste mai puțin.
- **Siguranță:** cheia se păstrează local, în baza de date a aplicației, și nu se afișează niciodată
  întreagă în interfață. Dacă modelul refuză o întrebare, o preia automat modelul de rezervă
  recomandat de Anthropic (`fallbacks: "default"`).
- **Teste:** `tests/test_ai.py` folosește un client simulat, deci rulează fără cheie și fără cost.

## Verificarea automată a Codului fiscal

În fiecare **luni dimineață**, o sarcină programată pe GitHub (`.github/workflows/fiscal-watch.yml`)
rulează `scripts/fiscal_watch.py`:

1. Claude caută pe internet modificări adoptate ale cotelor folosite de aplicație (TVA, impozit pe
   profit, dividende, micro, CAS, CASS, impozit pe venit, CAM), din surse oficiale.
2. Rezultatul e transformat în reguli JSON stricte și validat de aplicație (toate cotele, între 0 și 100).
3. Dacă există ceva nou, GitHub deschide o **propunere de modificare (pull request)** cu regula,
   explicațiile pentru Robert și linkurile la surse. Proprietarul repository-ului primește email.
4. Un om verifică sursele și apasă **Merge**. În cel mult 6 ore, toate aplicațiile se actualizează.

Nimic nu se aplică fără aprobare. Propunerile, proiectele și zvonurile neadoptate sunt ignorate.

**Configurare (o singură dată):**
- **Settings → Secrets and variables → Actions → New repository secret:** numele
  `ANTHROPIC_API_KEY`, valoarea cheia API Anthropic. Cheia nu se pune niciodată în cod.
- **Settings → Actions → General → Workflow permissions:** bifați „Allow GitHub Actions to create
  and approve pull requests”.
- Pentru o verificare imediată: tabul **Actions → Verificare Cod fiscal → Run workflow**.

O verificare costă câțiva cenți până la câteva zeci de cenți din contul Anthropic (căutări pe
internet plus răspunsul modelului `claude-opus-5-5`).

## Siguranță

- Un singur utilizator, cu parolă de cel puțin 8 caractere (PBKDF2), cod de recuperare și PIN opțional pe
  telefon. După 5 încercări greșite de pe același dispozitiv, intrarea de pe el se blochează 5 minute; după
  3 PIN-uri greșite se cere parola. Prima parolă se alege doar de pe calculatorul pe care rulează aplicația.
- Sesiunile expiră după 15 minute fără activitate (configurabil) și sunt păstrate doar ca amprentă.
  Schimbarea parolei scoate din aplicație toate celelalte dispozitive.
- Copiile de siguranță nu conțin cheia AI și nici sesiunile deschise.
- Aplicația răspunde doar la adrese IP, `localhost` și numele calculatorului (protecție la „DNS rebinding”).
  Alte nume se pot adăuga cu variabila `TESTIFY_ALLOWED_HOSTS`.
- Fișierele importate (Excel, CSV, e-Factura, arhive ZIP) sunt verificate: XML fără entități (defusedxml),
  limite de mărime, formule Excel neutralizate la export.
- În rețeaua de la birou, legătura dintre telefon și calculator este HTTP simplu: folosiți o rețea Wi-Fi cu
  parolă, fără acces pentru vizitatori.
- Regulile fiscale vin din acest repository: o modificare intră în aplicații doar după ce un om acceptă
  propunerea (pull request), deci accesul la contul GitHub trebuie păzit (autentificare în doi pași).

## Cum se calculează

- **Salariu:** CAS 25% și CASS 10% din brut; impozit pe venit 10% din (brut − CAS − CASS);
  firma plătește în plus CAM 2,25%. Costul pentru firmă = brut + CAM.
- **Marja brută** = venituri − costul mărfii vândute (cantitate × cost de achiziție). Marfa
  cumpărată intră în stoc și devine cost abia când se vinde.
- **Profit înainte de impozit** = marja brută − cheltuieli − salarii brute − CAM.
- **TVA de plată** = TVA din vânzări − TVA din achizițiile de marfă − TVA din cheltuieli
  (cote standard, redusă sau scutit, după tipul cheltuielii).
- **Impozit pe profit:** în rapoartele lunare, 16% din profitul lunii, ca la contabil. În
  **Calendarul fiscal** apare suma care se plătește efectiv, trimestrial: 16% din profitul cumulat
  de la începutul anului, minus ce s-a plătit în trimestrele anterioare; pierderile fiscale din anii
  trecuți se recuperează din cel mult 70% din profit. (Din Setări se poate trece pe regimul de
  microîntreprindere: 1% din venituri.)
- **Salariul minim** vine tot din regulile fiscale (4.050 lei, apoi 4.325 lei de la 1 iulie 2026),
  proporțional cu norma. Concediul fără plată scade brutul proporțional cu zilele lucrătoare lipsă.
- **Trezorerie:** totul cu TVA, pentru că asta se mișcă în cont; vânzările plătite pe loc și
  cheltuielile obișnuite se estimează din media ultimelor luni.
- **Termene:** pe 25 ale lunii următoare (D112, D300), pe 30 (D394); impozitul pe profit pe 25 ale
  lunii de după trimestru, iar trimestrul IV până pe 25 iunie, cu D101. Un termen care pică în
  weekend sau de sărbători se mută în prima zi lucrătoare.
- **Profit net** = profit înainte de impozit − impozit pe profit.
- **Îți rămâne ție** = profit net − impozitul pe dividende (16% din 2026).
- **Creanțe:** o factură către un client cu termen de plată rămâne „de încasat” până o marcați
  încasată; după scadență apare ca restantă.
- **Datorii la furnizori:** fiecare recepție de marfă primește scadența după termenul
  furnizorului (clientul plătește la 15–30 de zile) și rămâne „de plătit” până o marcați plătită.
- **Alerte de stoc:** fiecare produs are un stoc minim (implicit 5 bucăți pentru produsele noi);
  sub el, alerta apare în aplicație: la Testi, pe dashboard, la emiterea facturii și în pagina Stoc.
- La luna în curs, comparația se face cu aceeași perioadă din luna trecută.

Calculul e o estimare de gestiune, pentru imaginea de ansamblu: nu ține cont de deducerea
personală, de suma scutită de taxe la salariul minim, de indemnizația exactă de concediu medical,
de cheltuielile nedeductibile sau de facilitățile fiscale. Cifrele oficiale rămân cele ale contabilului.

## Tehnic

- **Server:** Python, FastAPI, SQLite (`app/`); verificarea regulilor fiscale rulează în fundal
- **Interfață:** HTML, CSS și JavaScript simplu, cu grafice Chart.js (inclus local, merge și fără internet)
- **Telefon:** manifest de aplicație web și service worker (`app/static/manifest.webmanifest`, `sw.js`)
- **Export:** openpyxl (Excel), reportlab (PDF)
- **Teste:** `pip install -r requirements-dev.txt && pytest` (rulează automat pe GitHub la fiecare modificare),
  inclusiv un test de performanță cu 5 ani de date și teste de interfață în care un browser real apasă
  butoanele (`tests/e2e`, cu Playwright)
- **Program Windows:** `pyinstaller testify.spec` (construit automat pe GitHub, pe un calculator Windows)
- **Siguranță:** jurnalul și închiderea lunii sunt triggere SQLite, deci se aplică oricum ar veni modificarea
