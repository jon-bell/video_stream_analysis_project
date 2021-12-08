IMAGE_SIZES = [0, 1, 2, 3]
FPS_OPTIONS = [15, 25, 30]
CPU_MEMORY_CONFIGS = {512: [1, 2], 1024: [2, 3], 2048: [4]}
# VIDEO_TYPE = ["LIVE", "PRERECORDED"]

file = open("../video_client/slurm_inputs.txt", "w")
task_count = 0
for image_size in IMAGE_SIZES:
    for fps in FPS_OPTIONS:
        for cpu, memory_list in CPU_MEMORY_CONFIGS.items():
            for memory in memory_list:
                config_string = " ".join(map(str, [image_size, fps, cpu, memory, f"task_{task_count}"]))
                file.write(config_string + "\n")
                print(config_string)
                task_count += 1
file.close()