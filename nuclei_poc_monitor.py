import os
import time
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

GIT_REPO = "https://github.com/projectdiscovery/nuclei-templates.git"
CLONE_DIR = "nuclei-templates"
POCS_SAVE_DIR = "nuclei_pocs"
OLD_FILELIST = "old_files.txt"
CHECK_INTERVAL = 300  # 每5分钟检测一次

def clone_or_pull_repo():
    if os.path.exists(CLONE_DIR):
        print("[+] 拉取最新模板更新...")
        subprocess.run(["git", "-C", CLONE_DIR, "pull"], stdout=subprocess.PIPE)
    else:
        print("[+] 克隆 nuclei-templates 仓库...")
        subprocess.run(["git", "clone", GIT_REPO], stdout=subprocess.PIPE)

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

def get_recent_yaml_commits(repo_dir, hours=24):
    since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    cmd = [
        "git", "-C", repo_dir, "log",
        f'--since={since_time}', '--name-status', '--pretty=format:'
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    new_yaml_files = set()

    for line in result.stdout.splitlines():
        if line.startswith("A") or line.startswith("M"):
            parts = line.split("\t", 1)
            if len(parts) == 2 and parts[1].endswith(".yaml"):
                new_yaml_files.add(os.path.join(repo_dir, parts[1]))
    return list(new_yaml_files)

def main_loop():
    while True:
        print(f"[+] 开始执行检测: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        clone_or_pull_repo()

        new_yaml_files = get_recent_yaml_commits(CLONE_DIR, hours=24)
        if new_yaml_files:
            print(f"[+] 发现过去24小时新增或更新的POC数量: {len(new_yaml_files)}，开始保存...")
            saved_paths = save_new_pocs(new_yaml_files)
            saved_paths.sort()
            print("[+] 本次新增或更新POC保存路径如下：")
            for path in saved_paths:
                print(path)
        else:
            print("[-] 无新增POC。")

        print(f"[+] 等待 {CHECK_INTERVAL / 60} 分钟后进行下一轮检测。\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main_loop()
