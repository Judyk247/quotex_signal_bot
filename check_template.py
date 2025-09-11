import os

def check_template():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
    INDEX_PATH = os.path.join(TEMPLATE_DIR, 'index.html')
    
    print(f"Base dir: {BASE_DIR}")
    print(f"Template dir: {TEMPLATE_DIR}")
    print(f"Index path: {INDEX_PATH}")
    print(f"Index exists: {os.path.exists(INDEX_PATH)}")
    
    if os.path.exists(TEMPLATE_DIR):
        print(f"Files in templates: {os.listdir(TEMPLATE_DIR)}")
    else:
        print("Templates directory not found!")
    
    print(f"Current dir files: {os.listdir('.')}")

if __name__ == "__main__":
    check_template()
