import time
from CPS import CPSClient

# 定义机器人连接参数
IP = '192.168.0.10'  # 替换为实际的机器人IP地址
PORT = 10003  # 机器人默认端口

# 创建CPS客户端对象并连接到机器人
cps = CPSClient()
ret = cps.HRIF_Connect(0, IP, PORT)  # 连接机器人控制器
if ret == 0:
    print("成功连接到机器人。")
else:
    print(f"连接机器人失败，错误码: {ret}")
    exit()  # 连接失败时退出程序

# 读取当前关节位置
RawACSpoints = []  # 存储关节位置的列表
status = cps.HRIF_ReadCmdJointPos(0, 0, RawACSpoints)  # 读取关节位置
if status == 0:  # 假设0表示读取成功
    RawACSpoints = [float(point) for point in RawACSpoints]  # 将读取的字符串转换为浮点数
    print("当前关节位置:", RawACSpoints)
else:
    print(f"读取关节位置失败，错误码: {status}")
    cps.HRIF_DisConnect(0)  # 读取失败时断开连接并退出
    exit()

# 定义运动参数
target_pose = RawACSpoints[-6:].copy()  # 目标位置，单位mm和度
target_pose[-4] = target_pose[-4] + 10
speed = 10  # 运动速度，单位mm/s
acceleration = 50  # 加速度，单位mm/s^2
ucs = "Base"  # 坐标系，需根据实际需求调整
radius = 0  # 直线运动半径，0表示直线运动
isSeek = 0  # 是否进行搜索运动
bit = 0  # 位标志
state = 1  # 运动状态
cmdID = 1  # 命令ID

# 控制机器人移动到目标位置
ret = cps.HRIF_MoveL(0, 0, points=target_pose, RawACSpoints=RawACSpoints[0:6], tcp="TCP", ucs=ucs,
                     speed=speed, Acc=acceleration, radius=radius, isSeek=isSeek, bit=bit, state=state, cmdID=cmdID)
if ret == 0:
    print("机器人正在移动到目标位置...")
    # 使用阻塞模式等待运动完成
    # 使用阻塞模式等待运动完成
    while True:
        motion_done_result = []  # 创建一个空列表用于存储结果
        motion_done = cps.HRIF_IsMotionDone(0, 0, motion_done_result)  # 检查运动是否完成
        if motion_done == 0:  # 假设0表示检查成功
            if motion_done_result[0] == 1:  # 假设motion_done_result[0] == 1 表示运动已完成
                print("运动已成功完成。")
                break
        elif motion_done < 0:  # 负值可能表示错误
            print(f"运动中出现错误，错误码: {motion_done}")
            break
        time.sleep(0.5)  # 设定状态查询的时间间隔，单位秒

else:
    print(f"机器人运动失败，错误码: {ret}")

# 读取并打印当前TCP姿态
current_pose = []
ret = cps.HRIF_ReadActTcpPos(0, 0, current_pose)  # 读取当前TCP姿态
if ret == 0:
    current_pose = [float(point) for point in current_pose]  # 将姿态值转换为浮点数
    print(f"当前TCP姿态: {current_pose}")
else:
    print(f"读取TCP姿态失败，错误码: {ret}")

# 断开与机器人的连接
cps.HRIF_DisConnect(0)
