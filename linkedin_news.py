import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import yagmail
from datetime import datetime

load_dotenv()

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# Lista de fuentes de LinkedIn a monitorear
LINKEDIN_SOURCES = [
    "https://www.linkedin.com/company/how-to-ai-guide/posts/?feedView=all&viewAsMember=true",
    "https://www.linkedin.com/in/zoranmilosevic/recent-activity/all/",
    "https://www.linkedin.com/company/whatisaimedia/posts/?feedView=all&viewAsMember=true",
    "https://www.linkedin.com/company/how-to-prompt/posts/?feedView=all&viewAsMember=true",
    "https://www.linkedin.com/company/ai-breaking/posts/?feedView=all&viewAsMember=true",
    "https://www.linkedin.com/in/midudev/recent-activity/all/"
]

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-extensions")
options.add_argument("--disable-infobars")
options.add_argument("--disable-webrtc")

options.add_argument("--headless")  
options.add_argument("--no-sandbox") 
options.add_argument("--disable-dev-shm-usage") 


driver = webdriver.Chrome(options=options)

def expand_publication(container):
    """Intenta expandir la publicación si tiene contenido colapsado"""
    try:
        see_more_buttons = container.find_elements(By.CSS_SELECTOR, ".feed-shared-inline-show-more-text__link")
        for button in see_more_buttons:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            button.click()
            time.sleep(1)
    except Exception:
        pass

def take_full_screenshot(container, filename):
    """Toma captura completa de la publicación con scroll"""
    try:
        expand_publication(container)
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
        time.sleep(1.5)
        
        container.screenshot(filename)
        
    except Exception as e:
        print(f"Error al capturar screenshot: {e}")
        container.screenshot(filename)

def get_source_name(url):
    """Extrae un nombre legible de la URL"""
    if "/company/" in url:
        return url.split("/company/")[1].split("/")[0].replace("-", " ").title()
    elif "/in/" in url:
        return url.split("/in/")[1].split("/")[0].replace("-", " ").title()
    return "LinkedIn Source"

try:
    print("🔐 Iniciando sesión en LinkedIn...")
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))

    driver.find_element(By.ID, "username").send_keys(LINKEDIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
    driver.find_element(By.ID, "password").send_keys(Keys.RETURN)

    WebDriverWait(driver, 10).until(EC.url_contains("/feed"))

    screenshot_files = []
    all_publications = []

    for source_url in LINKEDIN_SOURCES:
        source_name = get_source_name(source_url)
        print(f"📄 Cargando página de {source_name}...")
        
        try:
            driver.get(source_url)
            time.sleep(5)

            # Scroll para cargar más publicaciones
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.8);")
                time.sleep(2)

            print(f"📸 Tomando capturas de publicaciones de {source_name}...")
            publicaciones_containers = driver.find_elements(By.CSS_SELECTOR, ".feed-shared-update-v2")[:3]
            
            for idx, container in enumerate(publicaciones_containers, start=1):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_filename = f"pub_{source_name.replace(' ', '_')}_{idx}_{timestamp}.png"
                    
                    take_full_screenshot(container, screenshot_filename)
                    screenshot_files.append(screenshot_filename)

                    expand_publication(container)
                    text_element = container.find_element(By.CSS_SELECTOR, ".update-components-text")
                    text = text_element.text.strip()
                    
                    all_publications.append({
                        'source': source_name,
                        'text': text,
                        'screenshot': screenshot_filename
                    })

                except Exception as e:
                    print(f"Error al procesar publicación {idx} de {source_name}: {e}")
                    continue

        except Exception as e:
            print(f"Error al procesar fuente {source_name}: {e}")
            continue

    if not all_publications:
        all_publications.append({
            'source': "Sistema",
            'text': "No se encontraron publicaciones recientes en ninguna fuente.",
            'screenshot': None
        })

    contenido_html = """<html><body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h1 style="color: #0077b5;">Resumen de Publicaciones de LinkedIn</h1>
        <p style="color: #666;">Fecha: {date}</p>""".format(date=datetime.now().strftime("%d/%m/%Y %H:%M"))
    
    current_source = None
    for pub in all_publications:
        if pub['source'] != current_source:
            contenido_html += f"""
            <h2 style="margin-top: 30px; border-bottom: 2px solid #0077b5; padding-bottom: 5px; color: #333;">
                {pub['source']}
            </h2>"""
            current_source = pub['source']
        
        contenido_html += f"""
        <div style="margin-bottom: 40px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="padding: 15px;">
                <pre style="white-space: pre-wrap; font-family: inherit; margin: 0 0 15px 0;">{pub['text']}</pre>
                {f'<img src="cid:{os.path.basename(pub["screenshot"])}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">' if pub['screenshot'] else ''}
            </div>
        </div>"""
    
    contenido_html += "</body></html>"

    print("📧 Enviando correo...")
    yag = yagmail.SMTP(EMAIL_SENDER, EMAIL_PASSWORD)
    
    attachments = []
    for pub in all_publications:
        if pub['screenshot']:
            attachments.append(pub['screenshot'])

    yag.send(
        to=EMAIL_RECEIVER,
        subject=f"Resumen de publicaciones de LinkedIn - {datetime.now().strftime('%d/%m/%Y')}",
        contents=contenido_html,
        attachments=attachments,
        headers={"Content-Type": "text/html"}
    )

    print("✅ Correo enviado correctamente con capturas completas.")

except Exception as e:
    print(f"❌ Error crítico: {e}")

finally:
    # Limpiar archivos temporales
    for file in screenshot_files:
        try:
            os.remove(file)
        except:
            pass
    driver.quit()