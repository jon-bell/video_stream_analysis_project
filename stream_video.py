import uvicorn
from vidgear.gears.asyncio import WebGear_RTC

# various performance tweaks
options = {
    "frame_size_reduction": 25,
    "overwrite_default_files":True,
}

# initialize WebGear_RTC app
web = WebGear_RTC(source="video_test.mp4", logging=True, **options)

# run this app on Uvicorn server at address http://localhost:8000/
uvicorn.run(web(), host="localhost", port=8000)

# close app safely
web.shutdown()

if __name__ == '__main__':
    print("test")