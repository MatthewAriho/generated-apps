"""Cloud backup/restore using JSONBin.io free tier."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from datetime import datetime


class CloudSync:
    JSONBIN_URL = "https://api.jsonbin.io/v3/b"

    def __init__(self):
        self.api_key: str = ""
        self.bin_id: str = ""

    def set_credentials(self, api_key: str, bin_id: str = ""):
        self.api_key = api_key.strip()
        self.bin_id = bin_id.strip()

    @staticmethod
    def _encode(data: dict) -> str:
        return base64.b64encode(json.dumps(data).encode()).decode()

    @staticmethod
    def _decode(encoded: str) -> dict:
        return json.loads(base64.b64decode(encoded.encode()).decode())

    def backup(self, db_data: dict) -> dict:
        if not self.api_key:
            return {"success": False, "error": "No API key configured."}
        payload = json.dumps({
            "payload": self._encode(db_data),
            "backed_up_at": datetime.now().isoformat(),
            "schema_version": 2,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "X-Master-Key": self.api_key,
            "X-Bin-Private": "true",
        }
        try:
            if self.bin_id:
                url = f"{self.JSONBIN_URL}/{self.bin_id}"
                req = urllib.request.Request(url, data=payload, headers=headers, method="PUT")
            else:
                headers["X-Bin-Name"] = "ClearSpendBackup"
                req = urllib.request.Request(
                    self.JSONBIN_URL, data=payload, headers=headers, method="POST"
                )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if not self.bin_id and "metadata" in result:
                    self.bin_id = result["metadata"]["id"]
                return {"success": True, "bin_id": self.bin_id}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restore(self) -> dict:
        if not self.api_key or not self.bin_id:
            return {"success": False, "error": "API key and Bin ID required."}
        req = urllib.request.Request(
            f"{self.JSONBIN_URL}/{self.bin_id}/latest",
            headers={"X-Master-Key": self.api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                encoded = result["record"]["payload"]
                return {"success": True, "data": self._decode(encoded)}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
