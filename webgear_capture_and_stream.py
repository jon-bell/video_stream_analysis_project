import uvicorn, asyncio, cv2
from vidgear.gears.asyncio import WebGear
from vidgear.gears import ScreenGear
from live_generate_video import VideoGeneratorWorker
web = WebGear(logging=True)

async def my_frame_producer():
    # TODO: See if I can refactor this to look at a specific window instead of the whole monitor
    options = {"top": 500, "left": 500, "width": 470, "height": 500}
    stream = ScreenGear(monitor=1, logging=True, **options).start()
    while True:
        frame = stream.read()
        encodedImage = cv2.imencode(".jpg", frame)[1].tobytes()
        yield (b"--frame\r\nContent-Type:video/jpeg2000\r\n\r\n" + encodedImage + b"\r\n")
        await asyncio.sleep(0.00001)
    stream.release()

qr_code_generator = VideoGeneratorWorker(500, 500)
qr_code_generator.start()
web.config["generator"] = my_frame_producer
uvicorn.run(web(), host="localhost", port=8000)
web.shutdown()

