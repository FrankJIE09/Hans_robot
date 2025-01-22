import time
import random
import pandas as pd
import yaml  # 用于读取 YAML 配置
from CPS import CPSClient
# from hub_data_reader import read_average_data, parse_data  # 假设可以导入相关数据读取函数

# 读取配置文件
def load_config(config_file='config.yaml'):
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config.get('target_pose', [])
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return []

# 机器人连接参数
IP = '192.168.8.23'  # 替换为实际的机器人IP地址
PORT = 10003  # 机器人默认端口

# 初始化CPS客户端以控制机器人
cps = CPSClient()
ret = cps.HRIF_Connect(0, IP, PORT)  # 连接到机器人控制器
if ret != 0:
    print(f"连接机器人失败，错误码: {ret}")
    exit()

# 函数：测量重复精度
def measure_repeatability(port='COM3', iterations=10, target_pose=None):
    if not target_pose:
        print("未指定目标位置。请检查配置。")
        return pd.DataFrame()

    data_records = []  # 存储数据记录
    for i in range(iterations):
        print(f"开始第 {i + 1} 次测量...")

        # 移动机械臂到目标位置
        move_robot(cps, target_pose)

        # 向上移动 10 个单位
        adjusted_pose = target_pose.copy()
        adjusted_pose[-4] += 80  # 假设 -4 索引对应垂直方向
        move_robot(cps, adjusted_pose)

        # 在随机方向上移动
        random_movement(cps, adjusted_pose)

        # 返回到原始目标位置
        move_robot(cps, target_pose)

        # 读取千分表数据
        gauge_data = get_gauge_reading(port)
        if gauge_data is not None:
            data_records.append({
                'Iteration': i + 1,
                'Gauge Reading (mm)': gauge_data
            })
        else:
            print(f"第 {i + 1} 次读取数据失败")

    # 将数据保存到DataFrame中
    return pd.DataFrame(data_records)

# 函数：控制机械臂移动
def move_robot(cps_client, target_pose):
    speed = 50  # 运动速度
    acceleration = 500  # 加速度
    ucs = "Base"  # 坐标系
    radius = 0  # 直线运动半径
    ret = cps_client.HRIF_MoveL(0, 0, points=target_pose, RawACSpoints=target_pose, tcp="TCP", ucs=ucs,
                                speed=speed, Acc=acceleration, radius=radius, isSeek=0, bit=0, state=1, cmdID=1)
    if ret == 0:
        # 等待运动完成
        while True:
            motion_done_result = []
            motion_done = cps_client.HRIF_IsMotionDone(0, 0, motion_done_result)  # 检查运动是否完成
            if motion_done == 0 and motion_done_result and motion_done_result[0] == 1:
                break  # 运动完成
            elif motion_done < 0:
                print(f"运动过程中出错，错误码: {motion_done}")
                break
            time.sleep(0.5)  # 等待一段时间再次检查
    else:
        print(f"机器人运动失败，错误码: {ret}")

# 函数：随机方向上的移动
def random_movement(cps_client, current_pose):
    random_offsets = [random.uniform(-5, 5) for _ in range(len(current_pose))]  # 生成随机偏移值
    random_pose = [current_pose[i] + random_offsets[i] for i in range(len(current_pose))]
    move_robot(cps_client, random_pose)

# 函数：获取千分表读数
def get_gauge_reading(port):

    # response = read_average_data(port)  # 读取数据
    return 0  # 解析数据

# 加载目标位置配置
target_pose = load_config()

import os
import datetime

# 测量重复精度并保存数据
if target_pose:
    repeatability_data = measure_repeatability(target_pose=target_pose, iterations=2)

    # 创建文件夹路径（如不存在）
    os.makedirs('data', exist_ok=True)

    # 生成带时间戳的文件名并保存到data文件夹
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join('data', f'repeatability_results_{timestamp}.csv')

    # 保存数据
    repeatability_data.to_csv(output_filename, index=False)
    print(f"重复精度数据已保存到 '{output_filename}'。")
else:
    print("未加载到目标位置配置，无法进行测量。")

# 断开与机器人的连接
cps.HRIF_DisConnect(0)
