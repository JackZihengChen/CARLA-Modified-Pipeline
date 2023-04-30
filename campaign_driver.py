import argparse
import os
import subprocess

WEATHER_CODENAME = {"20 0 0 70 0 0 0 10": "clear-noon",
                    "100 100 100 70 0 100 10 70": "rain-noon",
                    "20 0 0 5 0 0 0 10": "clear-sunset",
                    "100 100 100 5 0 100 10 70": "rain-sunset",
                    "100 50 0 70 0 0 40 30": "haze-noon",
                    "100 50 0 5 0 0 40 30": "haze-sunset",
                    "20 0 0 -5 0 0 0 10": "clear-night",
                    "100 100 100 -5 0 100 10 70": "rain-night"}


def parse_routes(route_list_file):
    ret = list()
    if not os.path.isfile(route_list_file):
        print("Abort, list of routes not found.")
        return ret, ret
    f = open(route_list_file, "r")
    header = f.readline().strip().split(",")
    for line in f:
        line = line.strip().split(",")
        ret.append(line)
    return ret, header
        

def parse_weathers(weather_list_file):
    ret = list()
    if not os.path.isfile(weather_list_file):
        print("Abort, list of weathers not found.")
        return ret, ret
    f = open(weather_list_file, "r")
    header = f.readline().strip().split(",")
    for line in f:
        line = " ".join(line.strip().split(","))
        ret.append(line)
    return ret, header


def launch_subprocess(cmd):
    print("launching command:", cmd)
    try:
        subprocess.check_output(cmd, shell=True)
    except Exception as e:
        print("error running cmd, exception {}".format(e))


def run_campaign(route_list_file, weather_list_file, output_folder):
    routes, header = parse_routes(route_list_file)
    weathers, wea_header = parse_weathers(weather_list_file)

    if len(routes) == 0:
        print("Abort, no routes to run.")
        return
    
    cmd_base = "python3 leaderboard/leaderboard/leaderboard_evaluator.py --track=SENSORS --agent=image_agent --port "+os.environ['PORT']+" --trafficManagerSeed=0"
    if len(weathers) != 0:
        for route_tuple in routes:
            for weather in weathers:
                agent_weight = route_tuple[1]
                scenario = route_tuple[2]
                route = route_tuple[0]
                print("\n=====>starts running<=====")
                for head, config in zip(header, route_tuple):
                    print("{}: {}".format(head, config))
                for head, config in zip(wea_header, weather.split(" ")):
                    print("{}: {}".format(head, config))
                subpath = "{}_{}_{}_{}".format((route.split(".")[0]).split("/")[-1], agent_weight.split(".")[0],WEATHER_CODENAME[weather],scenario.split(".")[0])
                suboutput_folder = os.path.join(output_folder, subpath)
                checkpoint = os.path.join(suboutput_folder, ((route.split("/")[-1]).split("."))[0]+".txt")
                print("output folder:", suboutput_folder)
                cmd = cmd_base + " --routes=leaderboard/data/{} --agent-config={} --checkpoint={} \
                                   --weather_params {} --scenarios=leaderboard/data/{} --log_path={}".format(route, agent_weight, checkpoint, weather, scenario, suboutput_folder)
                if not os.path.isdir(suboutput_folder):
                    os.mkdir(suboutput_folder)
                if os.path.isfile(suboutput_folder + os.sep + "run.done"):
                    print("already finished continue, remove run.done file or output folder to force rerun")
                    continue
                try:
                    launch_subprocess(cmd)
                except:
                    continue
                ofh = open(suboutput_folder + os.sep + "run.done", 'w')
                ofh.close()
                print("------done running------")
    else:
        for route_tuple in routes:
            agent_weight = route_tuple[1]
            scenario = route_tuple[2]
            route = route_tuple[0]
            print("\n=====>starts running<=====")
            for head, config in zip(header, route_tuple):
                print("{}: {}".format(head, config))
            subpath = "{}_{}_{}".format((route.split(".")[0]).split("/")[-1], agent_weight.split(".")[0], scenario.split(".")[0])
            suboutput_folder = os.path.join(output_folder, subpath)
            print("output folder:", suboutput_folder)
            checkpoint = os.path.join(suboutput_folder, ((route.split("/")[-1]).split("."))[0]+".txt")
            cmd = cmd_base + " --routes=leaderboard/data/{} --agent-config={} --checkpoint={} \
                               --scenarios=leaderboard/data/{} --log_path={}".format(route, agent_weight, checkpoint, scenario, suboutput_folder)
            if not os.path.isdir(suboutput_folder):
                os.mkdir(suboutput_folder)
            if os.path.isfile(suboutput_folder + os.sep + "run.done"):
                print("already finished continue, remove run.done file to force rerun")
                continue
            try:
                launch_subprocess(cmd)
            except:
                continue
            ofh = open(suboutput_folder + os.sep + "run.done", 'w')
            ofh.close()
            print("------done running------")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser("campaign launcher")
    parser.add_argument("--routes_list", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--weathers_list", type=str, required=False, default="")
    args = parser.parse_args()
    run_campaign(args.routes_list, args.weathers_list, args.output_dir)
