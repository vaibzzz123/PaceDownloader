from qbittorrent import QbittorrentClient

class DownloadManager:
    def __init__(self, qbt_client: QbittorrentClient | None = None):
        self.qbt_client = qbt_client
    
    def download_episode(self, episode_id: int):
        # Logic to download episode using qBittorrent client
        pass
    
    def pause_episode(self, episode_id: int):
        # Logic to pause episode download using qBittorrent client
        pass
    
    def resume_episode(self, episode_id: int):
        # Logic to resume episode download using qBittorrent client
        pass
    
    def remove_episode(self, episode_id: int):
        # Logic to remove episode download using qBittorrent client
        pass
    
    def get_episode_status(self, episode_id: int):
        # Logic to check download status of an episode
        pass
    
    def list_active_downloads(self):
        # Logic to list all active downloads
        pass
    
    def _add_episode_to_data_location(self, episode_id: int):
        # Internal method to handle file placement after download
        pass