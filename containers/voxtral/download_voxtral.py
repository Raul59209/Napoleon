# download_voxtral.py

from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="mistralai/Voxtral-Mini-3B-2507",
    local_dir=r"C:\Users\raul5\.cache\huggingface\hub\models--mistralai--Voxtral-Mini-3B-2507",
    local_dir_use_symlinks=False,
)