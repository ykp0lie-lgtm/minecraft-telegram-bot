import requests
from config import Config

def offline_server_handler(func):
    def wrapper(self, *args, **kwargs):
        response_json = self._get_response_json()
        
        print(f"🔍 DEBUG - In offline_server_handler, response_json: {response_json}")
        
        # Check if the server is online
        if not response_json.get("online", False):
            error_msg = response_json.get("error", "Unknown error")
            # If error_msg is None, make it more descriptive
            if error_msg is None:
                error_msg = "No data received from any API"
            
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
        print(f"\n🔍 DEBUG START - Server address: {self.MINECRAFT_SERVER_ADDRESS}")
        
        # Split address for APIs that need separate IP and port
        if ':' in self.MINECRAFT_SERVER_ADDRESS:
            ip, port = self.MINECRAFT_SERVER_ADDRESS.split(':')
        else:
            ip = self.MINECRAFT_SERVER_ADDRESS
            port = '25565'
        
        print(f"🔍 DEBUG - IP: {ip}, Port: {port}")
        
        # List of APIs to try in order
        apis = [
            f"https://api.mcstatus.io/v2/status/java/{self.MINECRAFT_SERVER_ADDRESS}",
            f"https://api.mcsrvstat.us/2/{self.MINECRAFT_SERVER_ADDRESS}",
            f"https://mcapi.us/server/status?ip={ip}&port={port}",
            f"https://api.minetools.eu/ping/{ip}/{port}",
            # Add a simple test to see if we can reach anything
            f"https://api.mcsrvstat.us/2/mc.hypixel.net"  # Test with a known working server
        ]
        
        # Try each API until one works
        for i, api_url in enumerate(apis):
            try:
                print(f"\n🔍 DEBUG - Trying API #{i+1}: {api_url}")
                
                # Make the request with a timeout
                response = requests.get(api_url, timeout=10)
                print(f"🔍 DEBUG - Status code: {response.status_code}")
                print(f"🔍 DEBUG - Response headers: {dict(response.headers)}")
                print(f"🔍 DEBUG - Response text (first 500 chars): {response.text[:500]}")
                
                if response.status_code == 200:
                    try:
                        response_json = response.json()
                        print(f"🔍 DEBUG - JSON parsed successfully")
                        print(f"🔍 DEBUG - JSON keys: {response_json.keys()}")
                        
                        # Check if this is the test API (Hypixel)
                        if "mc.hypixel.net" in api_url:
                            print(f"🔍 DEBUG - TEST API RESULT (Hypixel): online={response_json.get('online')}")
                            print("✅ This proves the API itself works!")
                            continue  # Still try other APIs for your server
                        
                        normalized_data = self._normalize_api_response(api_url, response_json)
                        
                        if normalized_data:
                            print(f"🔍 DEBUG - Normalized data: {normalized_data}")
                            if normalized_data.get("online") is True:
                                print(f"✅ SUCCESS! API #{i+1} works!")
                                return normalized_data
                            else:
                                print(f"❌ API #{i+1} reports server offline: {normalized_data.get('error')}")
                        else:
                            print(f"❌ API #{i+1} normalization failed")
                            
                    except Exception as json_err:
                        print(f"🔍 DEBUG - JSON parse error: {str(json_err)}")
                else:
                    print(f"❌ API #{i+1} returned non-200 status")
                    
            except requests.exceptions.Timeout:
                print(f"❌ API #{i+1} timed out after 10 seconds")
            except requests.exceptions.ConnectionError:
                print(f"❌ API #{i+1} connection error - network issue")
            except Exception as e:
                print(f"❌ API #{i+1} failed with error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # If all APIs fail, return a standardized offline response
        print("\n❌ ALL APIS FAILED - Returning offline status")
        print(f"🔍 DEBUG - Final check: Can we reach the internet?")
        try:
            test = requests.get("https://api.mcsrvstat.us/2/mc.hypixel.net", timeout=5)
            print(f"🔍 DEBUG - Internet check: {test.status_code}")
            if test.status_code == 200:
                print("✅ Internet is working, APIs just don't like your server")
            else:
                print("❌ Internet check failed")
        except Exception as e:
            print(f"🔍 DEBUG - Internet check FAILED: {str(e)} - possible network issue in Railway!")
        
        return {
            "online": False,
            "players": {
                "online": 0,
                "max": 0,
                "list": []
            },
            "version": "Unknown",
            "error": f"Could not connect to any status API for {self.MINECRAFT_SERVER_ADDRESS}"
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
