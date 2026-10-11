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
# Oficiálně podporovaný a vysoce výkonný model pro kód přes Hugging Face router
MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct"
DOC_TITLE = "Známé chyby"
BETA_DIR = "plugin.video.streamcontinuum-beta"

STRUKTURA_BETA_PROJEKTU = [
    f"{BETA_DIR}/addon.py",
    f"{BETA_DIR}/addon.xml",
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

# --- DEFINICE NÁSTROJŮ PRO MODEL (TOOL CALLING) ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "ziskej_api_dokumentaci",
            "description": "Stáhne aktuální API dokumentaci pro danou službu, pokud ji potřebuješ k ověření syntaxe nebo parametrů.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zdroj": {
                        "type": "string",
                        "enum": ["kodi", "webshare", "trakt", "tmdb"],
                        "description": "Název dokumentace k načtení."
                    }
                },
                "required": ["zdroj"]
            }
        }
    }
]

def proved_stazeni_dokumentace(zdroj):
    urls = {
        "kodi": "https://kodi.wiki/view/Add-on_development",
        "webshare": "https://webshare.cz/apidoc/",
        "trakt": "https://developer.trakt.tv/",
        "tmdb": "https://developer.themoviedb.org/docs/getting-started"
    }
    target_url = urls.get(zdroj)
    if not target_url:
        return "Neznámý zdroj dokumentace."
    try:
        resp = requests.get(target_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return resp.text[:4000] if resp.status_code == 200 else f"Chyba při stahování: HTTP {resp.status_code}"
    except Exception as e:
        return f"Chyba připojení: {e}"

def nacti_google_doc():
    sa_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.readonly']
    )
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)
    
    query = f"name = '{DOC_TITLE}' and mimeType = 'application/vnd.google-apps.document'"
    results = drive_service.files().list(q=query, pageSize=1).execute()
    files = results.get('files', [])
    
    if not files:
        raise Exception(f"Google Dokument '{DOC_TITLE}' nebyl nalezen.")
        
    doc_id = files[0]['id']
    document = docs_service.documents().get(documentId=doc_id).execute()
    
    text = ""
    for element in document.get('body').get('content'):
        if 'paragraph' in element:
            for run in element['paragraph'].get('elements', []):
                if 'textRun' in run:
                    text += run['textRun'].get('content', '')
    return docs_service, doc_id, text

def aktualizuj_google_doc(docs_service, doc_id, novy_text):
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

def main():
    print("Spouštím autonomního AI agenta s podporou tool-callingu...")
    
    docs_service, doc_id, text_chyb = nacti_google_doc()
    github_issues = nacti_github_issues()
    beta_soubory = nacti_vsechny_soubory(STRUKTURA_BETA_PROJEKTU)
    
    system_instruction = (
        f"Jsi autonomní vývojový inženýr pro Kodi doplněk. Pracuješ VÝHRADNĚ ve složce '{BETA_DIR}/'.\n"
        "Pokud pro opravu kódu neznáš přesnou syntaxi nebo parametry API (Kodi, Webshare, Trakt, TMDb), "
        "využij dostupnou funkci 'ziskej_api_dokumentaci' a vyžádej si ji.\n\n"
        "STRIKTNÍ PRAVIDLA:\n"
        f"- Změny smíš provádět POUZE v souborech uvnitř adresáře '{BETA_DIR}/'.\n"
        "- ZÁKAZ zasahovat do 'addon.xml' (verzování spravuje externí skript).\n"
        "- Výstupní odpověď po dokončení analýzy a úprav vrať VÝHRADNĚ jako validní JSON objekt bez markdown formátování.\n\n"
        "Požadovaný formát JSON:\n"
        "{\n"
        '  "analyza": "Zhodnocení stavu a provedených kroků",\n'
        '  "vycisteny_text_dokumentu": "Aktualizovaný text pro Google Docs bez vyřešených chyb",\n'
        '  "nove_issue": { "vytvorit": false, "title": "", "body": "" },\n'
        '  "resene_issue_cislo": null,\n'
        '  "komentar_k_issue": null,\n'
        '  "commit_message": "Popis změn",\n'
        '  "zmeny": [\n'
        f'    {{ "cesta_k_souboru": "{BETA_DIR}/soubor.py", "novy_obsah": "kompletní nový obsah souboru" }}\n'
        '  ]\n'
        "}"
    )
    
    user_prompt = f"GOOGLE DOCS - ZNÁMÉ CHYBY:\n{text_chyb}\n\nGITHUB ISSUES:\n{json.dumps(github_issues)}\n\nKÓD BETY:\n{json.dumps(beta_soubory)}"
    
    client = OpenAI(base_url="https://router.huggingface.co/v1/", api_key=HF_TOKEN)
    
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]
    
    # 1. Kolo: Dotaz na model s podporou nástrojů
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    
    # Pokud model vyhodnotil potřebu dokumentace
    if response_message.tool_calls:
        messages.append(response_message)
        for tool_call in response_message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            
            if fn_name == "ziskej_api_dokumentaci":
                zdroj = fn_args.get("zdroj")
                print(f"Model si dynamicky vyžádal dokumentaci: {zdroj}")
                tool_output = proved_stazeni_dokumentace(zdroj)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": fn_name,
                    "content": tool_output
                })
                
        # 2. Kolo: Finální zpracování s načtenou dokumentací
        final_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            response_format={"type": "json_object"}
        )
        raw_output = final_response.choices[0].message.content
    else:
        raw_output = response_message.content

    cisty_json = raw_output.replace("```json", "").replace("```", "").strip()
    vysledek = json.loads(cisty_json)
    
    print("Analýza modelu:", vysledek.get("analyza"))
    
    # Aktualizace Google Docs
    if "vycisteny_text_dokumentu" in vysledek:
        aktualizuj_google_doc(docs_service, doc_id, vysledek["vycisteny_text_dokumentu"])
        print("Google Docs úspěšně aktualizován.")
        
    # Vytvoření GitHub Issue
    ni = vysledek.get("nove_issue")
    if ni and ni.get("vytvorit") and ni.get("title"):
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        requests.post(url, headers=headers, json={"title": ni["title"], "body": ni["body"]})
        print("Založeno nové GitHub Issue.")
        
    # Zápis změn do beta adresáře na GitHubu
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    for zmena in vysledek.get("zmeny", []):
        cesta = zmena["cesta_k_souboru"]
        
        if not cesta.startswith(BETA_DIR + "/") or cesta.endswith("addon.xml"):
            print(f"Ignorována neautorizovaná cesta nebo zakázaný soubor: {cesta}")
            continue
            
        stara_data = next((f for f in beta_soubory if f["cesta"] == cesta), None)
        sha = stara_data["sha"] if stara_data else None
        
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{cesta}"
        encoded_content = base64.b64encode(zmena["novy_obsah"].encode("utf-8")).decode("utf-8")
        
        payload = {
            "message": f"Konťa (Beta - Qwen): {vysledek.get('commit_message', 'Optimalizace')}",
            "content": encoded_content
        }
        if sha:
            payload["sha"] = sha
            
        requests.put(url, headers=headers, json=payload)
        print(f"Aktualizován soubor: {cesta}")
        
    # Komentář k vyřešenému Issue
    res_iss = vysledek.get("resene_issue_cislo")
    kom = vysledek.get("komentar_k_issue")
    if res_iss and kom:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{res_iss}/comments"
        requests.post(url, headers=headers, json={"body": kom})
        print(f"Přidán komentář k Issue #{res_iss}.")

if __name__ == "__main__":
    main()
