import time
import random
import pandas as pd
import yaml  # 用于读取 YAML 配置
from CPS import CPSClient
from hub_data_reader import read_average_data, parse_data  # 假设可以导入相关数据读取函数
import os
import datetime


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
# IP = '192.168.0.10'  # 替换为实际的机器人IP地址
IP = '192.168.8.23 '  # 替换为实际的机器人IP地址

PORT = 10003  # 机器人默认端口

# 初始化CPS客户端以控制机器人
cps = CPSClient()
ret = cps.HRIF_Connect(0, IP, PORT)  # 连接到机器人控制器
if ret != 0:
    print(f"连接机器人失败，错误码: {ret}")
    exit()


# 函数：获取机械臂末端位置和姿态
def get_end_effector_data(cps_client):
    RawACSpoints = [0] * 12  # 假设数据长度为12的占位符
    status = cps_client.HRIF_ReadCmdJointPos(0, 0, RawACSpoints)  # 读取关节位置和姿态
    if status == 0:  # 假设0表示读取成功
        RawACSpoints = [float(point) for point in RawACSpoints]  # 将读取的字符串转换为浮点数
        joint_angles = RawACSpoints[:6]  # 前6个数据为关节角度
        position_orientation = RawACSpoints[6:]  # 后6个数据为位置姿态信息
        return joint_angles, position_orientation
    else:
        print("读取关节和姿态信息失败")
        return [None] * 6, [None] * 6  # 返回默认值避免数据缺失


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
        initial_joint_angles, initial_position_orientation = get_end_effector_data(cps)  # 读取机械臂末端位置和姿态

        # 向上移动 80 个单位
        adjusted_pose = target_pose.copy()
        adjusted_pose[-4] += 80  # 假设 -4 索引对应垂直方向
        move_robot(cps, adjusted_pose)
        adjusted_joint_angles, adjusted_position_orientation = get_end_effector_data(cps)  # 读取调整后的机械臂末端数据

        # 在随机方向上移动
        random_pose = random_movement(cps, adjusted_pose)
        random_joint_angles, random_position_orientation = get_end_effector_data(cps)  # 读取随机移动后的机械臂数据

        # 返回到原始目标位置
        move_robot(cps, target_pose)
        return_joint_angles, return_position_orientation = get_end_effector_data(cps)  # 读取返回原位置的机械臂数据

        # 读取千分表数据
        data_record = {'Iteration': i + 1}  # 先添加迭代次数

        gauge_data = get_gauge_reading(port)
        # 添加单独的千分表读数
        if gauge_data is not None and isinstance(gauge_data, list):  # 确保gauge_data是列表
            for j, reading in enumerate(gauge_data):
                data_record[f'Gauge_{j + 1} Reading'] = reading
        else:
            print(f"第 {i + 1} 次读取数据失败")
            for j in range(6):  # 假设最多6个Gauge数据
                data_record[f'Gauge_{j + 1} Reading'] = None

        # 记录其他数据
        data_record.update({
            'Initial Target Pose': target_pose,
            'Adjusted Pose': adjusted_pose,
            'Random Pose': random_pose
        })

        # 分开保存关节角度和姿态信息
        for j, angle in enumerate(initial_joint_angles):
            data_record[f'Initial Joint Angle {j + 1}'] = angle
        for j, pos in enumerate(initial_position_orientation):
            data_record[f'Initial Position Orientation {j + 1}'] = pos
        for j, angle in enumerate(adjusted_joint_angles):
            data_record[f'Adjusted Joint Angle {j + 1}'] = angle
        for j, pos in enumerate(adjusted_position_orientation):
            data_record[f'Adjusted Position Orientation {j + 1}'] = pos
        for j, angle in enumerate(random_joint_angles):
            data_record[f'Random Joint Angle {j + 1}'] = angle
        for j, pos in enumerate(random_position_orientation):
            data_record[f'Random Position Orientation {j + 1}'] = pos
        for j, angle in enumerate(return_joint_angles):
            data_record[f'Return Joint Angle {j + 1}'] = angle
        for j, pos in enumerate(return_position_orientation):
            data_record[f'Return Position Orientation {j + 1}'] = pos

        data_records.append(data_record)

    # 将数据保存到DataFrame中
    return pd.DataFrame(data_records)


# 函数：控制机械臂移动
def move_robot(cps_client, target_pose):
    speed = 50  # 运动速度
    acceleration = 500  # 加速度
    ucs = "Base"  # 坐标系
    radius = 0  # 直线运动半径
    # 读取当前关节位置
    RawACSpoints = []  # 存储关节位置的列表
    status = cps.HRIF_ReadCmdJointPos(0, 0, RawACSpoints)  # 读取关节位置
    if status == 0:  # 假设0表示读取成功
        RawACSpoints = [float(point) for point in RawACSpoints]  # 将读取的字符串转换为浮点数
        # print("当前关节位置:", RawACSpoints)
    else:
        print(f"读取关节位置失败，错误码: {status}")
        cps.HRIF_DisConnect(0)  # 读取失败时断开连接并退出
        exit()
    ret = cps_client.HRIF_MoveL(0, 0, points=target_pose, RawACSpoints=RawACSpoints[0:6], tcp="TCP", ucs=ucs,
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
    return random_pose  # 返回随机偏移后的姿态


# 函数：获取千分表读数
def get_gauge_reading(port):
    response = read_average_data(port)  # 读取数据
    return response  # 解析数据


# 加载目标位置配置
target_pose = load_config()

# 测量重复精度并保存数据
if target_pose:
    repeatability_data = measure_repeatability(target_pose=target_pose, iterations=200)

    # 创建文件夹路径（如不存在）
    os.makedirs('data', exist_ok=True)

    # 生成带时间戳的文件名并保存到data文件夹
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join('data', f'repeatability_results_{timestamp}.csv')

    # 保存数据
    repeatability_data.to_csv(output_filename, index=False)
    print(f"重复精度数据已保存到 '{output_filename}'。")

    # 在程序结束前回到高度 +80 的位置
    height_adjusted_pose = target_pose.copy()
    height_adjusted_pose[-4] += 80  # 假设 -4 索引对应垂直方向
    move_robot(cps, height_adjusted_pose)

else:
    print("未加载到目标位置配置，无法进行测量。")

# 断开与机器人的连接
cps.HRIF_DisConnect(0)
