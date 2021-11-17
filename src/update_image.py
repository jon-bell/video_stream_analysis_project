import os
import subprocess
import argparse

def update_image(repository_name: str, docker_file_name: str = "Dockerfile", working_directory: str = os.getcwd(), region: str= "us-east-1",
                 aws_account_id: str = "843227719026", build_image: bool=True) -> None:
    os.chdir(working_directory)
    aws_ecr_address = f"{aws_account_id}.dkr.ecr.{region}.amazonaws.com"
    ecr_login_command = f"aws ecr get-login-password --region {region}  | docker login --username AWS --password-stdin {aws_ecr_address}"
    subprocess.run(ecr_login_command, shell=True)
    if build_image:
        build_docker_commmand = f"docker -f {docker_file_name} -t {repository_name}."
        subprocess.call(build_docker_commmand.split())
    full_repo_address = f"{aws_ecr_address}/{repository_name}:latest"
    tag_command = f"docker tag {repository_name}:latest {full_repo_address}"
    subprocess.call(tag_command.split())
    push_command = f"docker push {full_repo_address}"
    subprocess.call(push_command.split(" "))

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", default="Dockerfile", type=str, required=False, help="Provide a path to a file i.e dockerfile.opencv. Will default to 'Dockerfile'")
    parser.add_argument("-t", "--tag", type=str, required=True, help="Provide the tag/ the repository name for the image. i.e fargate-stream")
    parser.add_argument("-b", "--build-image", default=False, action="store_true", help="If flag is set then it will reubild the image, by default will not")
    return parser

def main() -> None:
    parser = get_parser()
    args = parser.parse_args()
    update_image(repository_name=args.tag, docker_file_name=args.filename, build_image=args.build_image)

if __name__ == '__main__':
    main()