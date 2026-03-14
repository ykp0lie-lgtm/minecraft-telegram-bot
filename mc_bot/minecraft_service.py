import requests
from config import Config

def offline_server_handler(func):
    def wrapper(self, *args, **kwargs):
        response_json = self._get_response_json()
        
        # Check if the server is online
        if not response_json.get("online", False):
            error_msg = response_json.get("error", "Server is offline or unreachable")
            return {
                "status": "error",
                "message": f"⚠️ Server status: {error_msg}"
            }
        
        return func(self, response_json, *args, **kwargs)
    return wrapper

class Minecraft_Status:
    def __init__(self):
        self.MINECRAFT_SERVER_ADDRESS = Config.MINECRAFT_SERVER_ADDRESS
    
    def _get_response_json(self):
        # List of APIs to try in order
        apis = [
            f"https://api.mcstatus.io/v2/status/java/{self.MINECRAFT_SERVER_ADDRESS}",
            f"https://api.mcsrvstat.us/2/{self.MINECRAFT_SERVER_ADDRESS}",
            f"https://mcapi.us/server/status?ip={self.MINECRAFT_SERVER_ADDRESS.split(':')[0]}&port={self.MINECRAFT_SERVER_ADDRESS.split(':')[1] if ':' in self.MINECRAFT_SERVER_ADDRESS else '25565'}",
            f"https://api.minetools.eu/ping/{self.MINECRAFT_SERVER_ADDRESS.split(':')[0]}/{self.MINECRAFT_SERVER_ADDRESS.split(':')[1] if ':' in self.MINECRAFT_SERVER_ADDRESS else '25565'}",
        ]
        
        # Try each API until one works
        for api_url in apis:
            try:
                print(f"Trying API: {api_url}")  # Debug output
                response = requests.get(api_url, timeout=5)  # 5 second timeout
                print(f"Response status: {response.status_code}")  # Debug output
                
                if response.status_code == 200:
                    response_json = response.json()
                    
                    # Different APIs return different formats, let's normalize them
                    normalized_data = self._normalize_api_response(api_url, response_json)
                    
                    if normalized_data and normalized_data.get("online") is not None:
                        print(f"Success with API: {api_url}")  # Debug output
                        return normalized_data
                        
            except Exception as e:
                print(f"API {api_url} failed: {str(e)}")  # Debug output
                continue
        
        # If all APIs fail, return a standardized offline response
        print("All APIs failed, returning offline status")
        return {
            "online": False,
            "players": {
                "online": 0,
                "max": 0,
                "list": []
            },
            "version": "Unknown",
            "error": "Could not connect to any status API"
        }

    def _normalize_api_response(self, api_url, response_json):
        """
        Convert different API response formats to a standard format
        """
        try:
            normalized = {
                "online": False,
                "players": {
                    "online": 0,
                    "max": 0,
                    "list": []
                },
                "version": "Unknown",
                "error": None
            }
            
            # mcstatus.io format
            if "api.mcstatus.io" in api_url:
                normalized["online"] = response_json.get("online", False)
                if normalized["online"]:
                    players = response_json.get("players", {})
                    normalized["players"]["online"] = players.get("online", 0)
                    normalized["players"]["max"] = players.get("max", 0)
                    normalized["players"]["list"] = [p.get("name") for p in players.get("list", [])]
                    normalized["version"] = response_json.get("version", {}).get("name", "Unknown")
            
            # mcsrvstat.us format
            elif "mcsrvstat.us" in api_url:
                normalized["online"] = response_json.get("online", False)
                if normalized["online"]:
                    players = response_json.get("players", {})
                    normalized["players"]["online"] = players.get("online", 0)
                    normalized["players"]["max"] = players.get("max", 0)
                    normalized["players"]["list"] = players.get("list", [])
                    normalized["version"] = response_json.get("version", "Unknown")
            
            # mcapi.us format
            elif "mcapi.us" in api_url:
                normalized["online"] = response_json.get("status", False)
                if normalized["online"]:
                    players = response_json.get("players", {})
                    normalized["players"]["online"] = players.get("now", 0)
                    normalized["players"]["max"] = players.get("max", 0)
                    # mcapi.us doesn't provide player list in free tier
                    normalized["players"]["list"] = []
                    normalized["version"] = response_json.get("server", {}).get("name", "Unknown")
            
            # minetools.eu format
            elif "minetools.eu" in api_url:
                # This API returns error field if server is offline
                if "error" not in response_json:
                    normalized["online"] = True
                    normalized["players"]["online"] = response_json.get("players", {}).get("online", 0)
                    normalized["players"]["max"] = response_json.get("players", {}).get("max", 0)
                    
                    # Handle player list format from minetools
                    player_sample = response_json.get("players", {}).get("sample", [])
                    if player_sample and isinstance(player_sample, list):
                        normalized["players"]["list"] = [p.get("name") for p in player_sample if isinstance(p, dict)]
                    
                    normalized["version"] = response_json.get("version", {}).get("name", "Unknown")
                else:
                    normalized["error"] = response_json.get("error", "Server offline")
            
            return normalized
            
        except Exception as e:
            print(f"Error normalizing API response: {str(e)}")
            return None

    @offline_server_handler
    def get_online_users_count(self, response_json):
        return {
            "status": "success",
            "online_users_count": response_json.get("players", {}).get("online", 0)
        }

    @offline_server_handler
    def get_online_users_names(self, response_json):
        # Get the player list
        player_list = response_json.get("players", {}).get("list", [])
        
        # Handle case where player list might be empty or None
        if not player_list:
            player_list = []
        
        return {
            "status": "success",
            "online_users_names": player_list
        }
