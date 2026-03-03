from broadcaster import Broadcaster

# One broadcaster per SSE endpoint/topic.
# Import these directly in any module that needs to publish or subscribe.
downloads_broadcaster = Broadcaster()
metadata_broadcaster = Broadcaster()
