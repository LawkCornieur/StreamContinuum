import os
import json
import base64
import re
import requests
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- KONFIGURACE ---
HF_TOKEN = os.getenv("HF_TOKEN")
GITHUB_TOKEN = os.getenv("GH_TOKEN")
REPO_OWNER = "LawkCornieur"
REPO_NAME = "StreamContinuum"
MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct"
DOC_TITLE = "Známé chyby"

STRUKTURA_BETA_PROJEKTU = [
    "plugin.video.streamcontinuum-beta/addon.py",
    "plugin.video.streamcontinuum-beta/addon.xml",
    "plugin.video.streamcontinuum-beta/service.py",
    "plugin.video.streamcontinuum-beta/resources/settings.xml",
    "plugin.video.streamcontinuum-beta/resources/language/resource.language.cs_cz/strings.po",
    "plugin.video.streamcontinuum-beta/resources/language/resource.language.de_de/strings.po",
    "plugin.video.streamcontinuum-beta/resources/language/resource.language.en_gb/strings.po",
    "plugin.video.streamcontinuum-beta/resources/lib/history.py",
    "plugin.video.streamcontinuum-beta/resources/lib/md5crypt.py",
    "plugin.video.streamcontinuum-beta/resources/lib/sync.py",
    "plugin.video.streamcontinuum-beta/resources/lib/tmdb.py",
    "plugin.video.streamcontinuum-beta/resources/lib/trakt.py",
    "plugin.video.streamcontinuum-beta/resources/lib/webshare.py"
]

def nacti_google_doc():
    """Načte obsah a ID Google Dokumentu 'Známé chyby'."""
    sa_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.readonly']
    )
    
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)
    
    # Vyhledání dokumentu podle názvu
    query = f"name = '{DOC_TITLE}' and mimeType = 'application/vnd.google-apps.document'"
    results = drive_service.files().list(q=query, pageSize=1).execute()
    files = results.get('files', [])
    
    if not files:
        raise Exception(f"Google Dokument '{DOC_TITLE}' nebyl nalezen nebo k němu nemá servisní účet přístup.")
        
    doc_id = files[0]['id']
    document = docs_service.documents().get(documentId=doc_id).execute()
    
    # Extrakce textu z dokumentu
    text = ""
    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            for run in element['paragraph'].get('elements', []):
                if 'textRun' in run:
                    text += run['textRun'].get('content', '')
                    
    return docs_service, doc_id, text

def aktualizuj_google_doc(docs_service, doc_id, novy_text):
    """Přepíše obsah Google Dokumentu vyčištěným textem."""
    document = docs_service.documents().get(documentId=doc_id).execute()
    end_index = document.get('body').get('content')[-1].get('endIndex', 1)
    
    requests_body = []
    if end_index > 1:
        requests_body.append({'deleteContentRange': {'range': {'startIndex': 1, 'endIndex': end_index - 1}}})
    if novy_text:
        requests_body.append({'insertText': {'location': {'index': 1}, 'text': novy_text}})
        
    docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests_body}).execute()

def stahni_dokumentaci():
    """Stáhne klíčové API dokumentace pro přesný vývoj."""
    urls = {
        "Kodi Wiki": "https://kodi.wiki/view/Add-on_development",
        "Webshare": "https://webshare.cz/apidoc/",
        "Trakt": "https://developer.trakt.tv/",
        "TMDb": "https://developer.themoviedb.org/docs/getting-started"
    }
    docs_text = ""
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for nazev, url in urls.items():
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                docs_text += f"\n=== {nazev} ===\n{resp.text[:4000]}\n"
        except Exception as e:
                docs_text += f"\n=== {nazev} (Nelze načíst: {e}) ===\n"
    return docs_text

def nacti_github_issues():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues?state=open"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return [{"number": i["number"], "title": i["title"], "body": i["body"]} for i in resp.json()]
    return []

def nacti_vsechny_soubory(soubory):
    vysledek = []
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    for cesta in soubory:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{cesta.strip()}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            decoded_content = base64.b64decode(data["content"]).decode("utf-8")
            vysledek.append({"cesta": cesta, "sha": data["sha"], "content": decoded_content})
        else:
            vysledek.append({"cesta": cesta, "sha": None, "content": ""})
    return vysledek

def ziskej_verzi_z_addon_xml(soubory):
    for f in soubory:
        if f["cesta"].endswith("addon.xml"):
            m = re.search(r'version="([^"]+)"', f["content"])
            if m:
                return m.group(1)
    return "Neznámá verze"

def main():
    print("Spouštím AI vývojového agenta...")
    
    docs_service, doc_id, text_chyb = nacti_google_doc()
    api_docs = stahni_dokumentaci()
    github_issues = nacti_github_issues()
    beta_soubory = nacti_vsechny_soubory(STRUKTURA_BETA_PROJEKTU)
    aktualni_verze = ziskej_verzi_z_addon_xml(beta_soubory)
    
    system_instruction = (
        f"Jsi autonomní vývojový inženýr pro Kodi doplněk StreamContinuum-Beta.\n"
        f"Máš k dispozici referenční dokumentace:\n{api_docs}\n\n"
        "Analyzuj známé chyby z Google Docs, otevřená GitHub Issues a zdrojový kód.\n"
        "Vrať odpověď VÝHRADNĚ jako validní JSON objekt bez jakéhokoliv formátování markdown (žádné ```json).\n"
        "Formát JSON:\n"
        "{\n"
        '  "analyza": "Zhodnocení stavu",\n'
        '  "vycisteny_text_dokumentu": "Aktualizovaný text pro Google Docs bez vyřešených chyb",\n'
        '  "nove_issue": { "vytvorit": false, "title": "", "body": "" },\n'
        '  "resene_issue_cislo": null,\n'
        '  "komentar_k_issue": null,\n'
        '  "commit_message": "Popis změn",\n'
        '  "zmeny": [\n'
        '    { "cesta_k_souboru": "cesta", "novy_obsah": "kompletní nový obsah souboru" }\n'
        '  ]\n'
        "}"
    )
    
    user_prompt = f"GOOGLE DOCS - ZNÁMÉ CHYBY:\n{text_chyb}\n\nGITHUB ISSUES:\n{json.dumps(github_issues)}\n\nKÓD BETY:\n{json.dumps(beta_soubory)}"
    
    client = OpenAI(base_url="[https://router.huggingface.co/v1](https://router.huggingface.co/v1)", api_key=HF_TOKEN)
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    vysledek = json.loads(response.choices.message.content)
    print("Analýza modelu:", vysledek.get("analyza"))
    
    # 1. Zápis vyčištěného dokumentu zpět do Google Docs
    if "vycisteny_text_dokumentu" in vysledek:
        aktualizuj_google_doc(docs_service, doc_id, vysledek["vycisteny_text_dokumentu"])
        print("Google Docs úspěšně aktualizován.")
        
    # 2. Vytvoření nového Issue pokud je požadováno
    ni = vysledek.get("nove_issue")
    if ni and ni.get("vytvorit") and ni.get("title"):
        url = f"[https://api.github.com/repos/](https://api.github.com/repos/){REPO_OWNER}/{REPO_NAME}/issues"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        requests.post(url, headers=headers, json={"title": ni["title"], "body": ni["body"]})
        print("Založeno nové GitHub Issue.")
        
    # 3. Zápis změn v kódu na GitHub
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    for zmena in vysledek.get("zmeny", []):
        cesta = zmena["cesta_k_souboru"]
        if cesta.endswith("addon.xml"):
            continue
            
        stara_data = next((f for f in beta_soubory if f["cesta"] == cesta), None)
        sha = stara_data["sha"] if stara_data else None
        
        url = f"[https://api.github.com/repos/](https://api.github.com/repos/){REPO_OWNER}/{REPO_NAME}/contents/{cesta}"
        encoded_content = base64.b64encode(zmena["novy_obsah"].encode("utf-8")).decode("utf-8")
        
        payload = {
            "message": f"Konťa (Beta - Qwen): {vysledek.get('commit_message', 'Optimalizace')}",
            "content": encoded_content
        }
        if sha:
            payload["sha"] = sha
            
        requests.put(url, headers=headers, json=payload)
        print(f"Aktualizován soubor: {cesta}")
        
    # 4. Komentář k řešenému Issue
    res_iss = vysledek.get("resene_issue_cislo")
    kom = vysledek.get("komentar_k_issue")
    if res_iss and kom:
        url = f"[https://api.github.com/repos/](https://api.github.com/repos/){REPO_OWNER}/{REPO_NAME}/issues/{res_iss}/comments"
        requests.post(url, headers=headers, json={"body": kom})
        print(f"Přidán komentář k Issue #{res_iss}.")

if __name__ == "__main__":
    main()
