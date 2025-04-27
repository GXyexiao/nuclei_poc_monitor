import os
import time
import requests
import zipfile
import shutil
import difflib
from datetime import datetime

GITHUB_ZIP_URL = "https://github.com/projectdiscovery/nuclei-templates/archive/refs/heads/master.zip"
CHECK_INTERVAL = 3600  # 多久一次，这里是1小时
TEMPLATES_DIR = "nuclei-templates-master"
POCS_SAVE_DIR = "nuclei_pocs"
OLD_FILELIST = "old_files.txt"


def download_templates_zip():
    print("[+] 正在下载最新的nuclei-templates...")
    response = requests.get(GITHUB_ZIP_URL)
    with open("templates.zip", "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile("templates.zip", 'r') as zip_ref:
        zip_ref.extractall(".")
    os.remove("templates.zip")
    print("[+] 下载并解压完成。")


def get_all_yaml_files(root_dir):
    yaml_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".yaml") or file.endswith(".yml"):
                yaml_files.append(os.path.join(root, file))
    return yaml_files


def extract_id_from_yaml(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("id:"):
                    return line.strip().split(":", 1)[1].strip()
    except Exception as e:
        print(f"[-] 提取ID失败: {file_path}, 错误: {e}")
    return None


def sanitize_filename(name):
    return name.replace('/', '_').replace('\\', '_').replace(':', '_')


def save_new_pocs(new_files):
    if not os.path.exists(POCS_SAVE_DIR):
        os.makedirs(POCS_SAVE_DIR)

    saved_paths = []

    for file in new_files:
        id_or_name = extract_id_from_yaml(file)
        if not id_or_name:
            id_or_name = os.path.basename(file).replace('.yaml', '').replace('.yml', '')
        safe_name = sanitize_filename(id_or_name)
        save_path = os.path.join(POCS_SAVE_DIR, safe_name + ".yaml")
        try:
            shutil.copy(file, save_path)
            saved_paths.append(save_path)
        except Exception as e:
            print(f"[-] 保存POC失败: {file}, 错误: {e}")

    return saved_paths


def save_current_file_list(file_list):
    with open(OLD_FILELIST, 'w', encoding='utf-8') as f:
        for file in file_list:
            f.write(file + '\n')


def load_old_file_list():
    if not os.path.exists(OLD_FILELIST):
        return []
    with open(OLD_FILELIST, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f]


def main_loop():
    while True:
        print(f"[+] 开始执行检测: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if os.path.exists(TEMPLATES_DIR):
            shutil.rmtree(TEMPLATES_DIR)

        download_templates_zip()

        current_files = get_all_yaml_files(TEMPLATES_DIR)
        old_files = load_old_file_list()

        new_files = list(set(current_files) - set(old_files))

        if new_files:
            print(f"[+] 本次检测到新增POC数量: {len(new_files)}，开始保存...")
            saved_paths = save_new_pocs(new_files)
            saved_paths.sort()
            print("[+] 本次新增POC保存路径如下：")
            for path in saved_paths:
                print(path)
        else:
            print("[-] 本次未发现新增POC。")

        save_current_file_list(current_files)

        print(f"[+] 等待 {CHECK_INTERVAL/60} 分钟后进行下一轮检测。\n")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main_loop()
