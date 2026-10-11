import os
import json
import base64
import requests
from huggingface_hub import InferenceClient
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- KONFIGURACE ---
HF_TOKEN = os.getenv("HF_TOKEN")
GITHUB_TOKEN = os.getenv("GH_TOKEN")
REPO_OWNER = "LawkCornieur"
REPO_NAME = "StreamContinuum"
# Zůstáváme u špičkového kódovacího modelu, který je na HF perfektně optimalizován
MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct"

DOC_TITLE_CHYBY = "Známé chyby"
DOC_TITLE_WEBSHARE = "API Webshare"
BETA_DIR = "plugin.video.streamcontinuum-beta"

POVOLENE_SOUBORY = [
    f"{BETA_DIR}/addon.py",
    f"{BETA_DIR}/service.py",
    f"{BETA_DIR}/resources/settings.xml",
    f"{BETA_DIR}/resources/language/resource.language.cs_cz/strings.po",
    f"{BETA_DIR}/resources/language/resource.language.de_de/strings.po",
    f"{BETA_DIR}/resources/language/resource.language.en_gb/strings.po",
    f"{BETA_DIR}/resources/lib/history.py",
    f"{BETA_DIR}/resources/lib/md5crypt.py",
    f"{BETA_DIR}/resources/lib/sync.py",
    f"{BETA_DIR}/resources/lib/tmdb.py",
    f"{BETA_DIR}/resources/lib/trakt.py",
    f"{BETA_DIR}/resources/lib/webshare.py"
]

def optimalizuj_text(text):
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def nacti_google_doc(doc_title):
    sa_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.readonly']
    )
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)
    
    query = f"name = '{doc_title}' and mimeType = 'application/vnd.google-apps.document'"
    results = drive_service.files().list(q=query, pageSize=1).execute()
    files = results.get('files', [])
    
    if not files:
        return None, None, ""
        
    doc_id = files[0]['id']
    document = docs_service.documents().get(documentId=doc_id).execute()
    
    text = ""
    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            for run in element['paragraph'].get('elements', []):
                if 'textRun' in run:
                    text += run['textRun'].get('content', '')
                    
    return docs_service, doc_id, optimalizuj_text(text)

def aktualizuj_google_doc(docs_service, doc_id, novy_text):
    if not docs_service or not doc_id:
        return
    document = docs_service.documents().get(documentId=doc_id).execute()
    end_index = document.get('body').get('content')[-1].get('endIndex', 1)
    
    requests_body = []
    if end_index > 1:
        requests_body.append({'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_index - 1}}})
    if novy_text:
        requests_body.append({'insertText': {'location': {'index': 1}, 'text': novy_text}})
    docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests_body}).execute()

def nacti_github_issues():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues?state=open"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return [{"number": i["number"], "title": i["title"], "body": i["body"]} for i in resp.json()]
    return []

def nacti_konkretni_soubor(cesta):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{cesta.strip()}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        decoded_content = base64.b64decode(data["content"]).decode("utf-8")
        return {"cesta": cesta, "sha": data["sha"], "content": decoded_content}
    return {"cesta": cesta, "sha": None, "content": ""}

def main():
    print("Spouštím agenta přes oficiální Hugging Face InferenceClient...")
    
    docs_service_chyby, doc_id_chyby, text_chyb = nacti_google_doc(DOC_TITLE_CHYBY)
    _, _, text_webshare_tahak = nacti_google_doc(DOC_TITLE_WEBSHARE)
    github_issues = nacti_github_issues()
    
    predpripraveny_kod = {}
    for cesta in [f"{BETA_DIR}/resources/lib/sync.py", f"{BETA_DIR}/resources/lib/webshare.py"]:
        info = nacti_konkretni_soubor(cesta)
        if info["content"]:
            predpripraveny_kod[cesta] = info["content"]

    system_instruction = (
        f"Jsi zkušený vývojový inženýr pro Kodi doplněk. Pracuješ VÝHRADNĚ ve složce '{BETA_DIR}/'.\n"
        "1. Respektuj existující strukturu projektu. NIKDY nevytvářej importy neexistujících modulů (např. žádný modul 'utils' neexistuje).\n"
        "2. Pro správu chyb a úkolů zakládej GitHub Issues a po jejich vyřešení je uzavírej (přidej komentář a nastav resene_issue_cislo).\n"
        "3. Google Doc 'Známé chyby' udržuj čistý a přehledný jako seznam aktuálních vývojových cílů.\n\n"
        "STRIKTNÍ PRAVIDLA:\n"
        f"- Změny smíš provádět POUZE v souborech uvnitř adresáře '{BETA_DIR}/'.\n"
        "- ZÁKAZ zasahovat do 'addon.xml'.\n"
        "- Odpověď vrať VÝHRADNĚ jako validní JSON bez markdownu.\n\n"
        "Formát JSON:\n"
        "{\n"
        '  "analyza": "Stručné zhodnocení problému",\n'
        '  "vycisteny_text_dokumentu": "Aktualizovaný čistý text pro Google Docs",\n'
        '  "nove_issue": { "vytvorit": false, "title": "", "body": "" },\n'
        '  "resene_issue_cislo": null,\n'
        '  "komentar_k_issue": "Popis řešení pro uzavření issue",\n'
        '  "commit_message": "Popis změn",\n'
        '  "zmeny": [\n'
        f'    {{ "cesta_k_souboru": "{BETA_DIR}/resources/lib/sync.py", "novy_obsah": "celý opravený kód souboru" }}\n'
        '  ]\n'
        "}"
    )
    
    user_prompt = (
        f"CÍLE V GOOGLE DOCS:\n{text_chyb}\n\n"
        f"API TAHÁK WEBSHARE:\n{text_webshare_tahak}\n\n"
        f"OTEVŘENÁ GITHUB ISSUES:\n{json.dumps(github_issues)}\n\n"
        f"AKTUÁLNÍ KÓD SOUBORŮ:\n{json.dumps(predpripraveny_kod)}"
    )
    
    # Inicializace oficiálního HF klienta s využitím PRO tokenu
    client = InferenceClient(model=MODEL_NAME, token=HF_TOKEN)
    
    response = client.chat_completion(
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=4000
    )
    
    raw_output = response.choices[0].message.content
    vysledek = json.loads(raw_output.replace("```json", "").replace("```", "").strip())
    
    print("Analýza modelu:", vysledek.get("analyza"))
    
    if "vycisteny_text_dokumentu" in vysledek and docs_service_chyby:
        aktualizuj_google_doc(docs_service_chyby, doc_id_chyby, vysledek["vycisteny_text_dokumentu"])
        print("Google Docs aktualizován.")
        
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    ni = vysledek.get("nove_issue")
    if ni and ni.get("vytvorit") and ni.get("title"):
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
        requests.post(url, headers=headers, json={"title": ni["title"], "body": ni["body"]})
        print("Založeno nové GitHub Issue.")
        
    for zmena in vysledek.get("zmeny", []):
        cesta = zmena.get("cesta_k_souboru") or zmena.get("cesta") or zmena.get("path")
        novy_obsah = zmena.get("novy_obsah") or zmena.get("obsah")
        
        if not cesta or not novy_obsah:
            continue
            
        if cesta not in POVOLENE_SOUBORY:
            print(f"Ignorována neautorizovaná cesta: {cesta}")
            continue
            
        aktualni_info = nacti_konkretni_soubor(cesta)
        sha = aktualni_info["sha"]
        
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{cesta}"
        encoded_content = base64.b64encode(novy_obsah.encode("utf-8")).decode("utf-8")
        
        payload = {
            "message": f"Konťa (Beta - Qwen): {vysledek.get('commit_message', 'Oprava')}",
            "content": encoded_content
        }
        if sha:
            payload["sha"] = sha
            
        requests.put(url, headers=headers, json=payload)
        print(f"Aktualizován soubor: {cesta}")
        
    res_iss = vysledek.get("resene_issue_cislo")
    kom = vysledek.get("komentar_k_issue")
    if res_iss and kom:
        url_kom = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{res_iss}/comments"
        requests.post(url_kom, headers=headers, json={"body": kom})
        
        url_close = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{res_iss}"
        requests.patch(url_close, headers=headers, json={"state": "closed"})
        print(f"Issue #{res_iss} vyřešeno, uzavřeno a opatřeno komentářem.")

if __name__ == "__main__":
    main()
