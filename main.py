# 导入CPS库
import time

from CPS import CPSClient

# 定义IP和端口
IP = '192.168.0.10'  # 替换为实际的机器人IP
PORT = 10003  # 默认端口

# 创建CPS客户端对象
cps = CPSClient()

# 连接机器人控制器
ret = cps.HRIF_Connect(0, IP, PORT)
if ret == 0:
    print("成功连接到机器人")
else:
    print(f"连接失败，错误码: {ret}")
    exit()

# 使能机器人
# ret = cps.HRIF_GrpEnable(0, 0)
# if ret == 0:
#     print("机器人已使能")
# else:
#     print(f"机器人使能失败，错误码: {ret}")
#     cps.HRIF_DisConnect(0)
#     exit()
# Example call to read current joint positions
RawACSpoints = []
status = cps.HRIF_ReadCmdJointPos(0, 0, RawACSpoints)
RawACSpoints = [float(point) for point in RawACSpoints]

# Check if the status indicates a successful read
if status == 0:  # Assuming 0 indicates success, modify based on your API's status codes
    print("Current joint positions:", RawACSpoints)
# 设置目标位置（示例值，需根据实际情况调整）
target_pose = [87.258+10, 19.033, 110.843, 180.000, -88.200, 12.497]  # 目标位置，单位mm和度
speed = 10  # 运动速度，单位mm/s
acceleration = 50  # 加速度，单位mm/s^2
ucs = 0  # 坐标系
radius = 0  # 圆弧半径，为0表示直线
isSeek = 0  # 是否搜索
bit = 0  # 位标记
state = 1  # 状态
cmdID = 1  # 命令ID

# 使用HRIF_MoveL移动机器人到目标位置
#    def HRIF_MoveL(self, boxID, rbtID, points, RawACSpoints, tcp, ucs, speed, Acc, radius, isSeek, bit, state, cmdID):
ret = cps.HRIF_MoveL(0, 0, points=target_pose, RawACSpoints=RawACSpoints[0:6], tcp="TCP", ucs="Base",
                     speed=speed, Acc=acceleration, radius=radius, isSeek=isSeek, bit=bit, state=state, cmdID=cmdID)
if ret == 0:
    print("机器人已移动到目标位置")
else:
    print(f"运动失败，错误码: {ret}")
time.sleep(10)
# 读取当前姿态
current_pose = []
ret = cps.HRIF_ReadActTcpPos(0, 0, current_pose)
current_pose = [float(point) for point in current_pose]

if ret == 0:
    print(f"当前TCP姿态: {current_pose}")
else:
    print(f"读取姿态失败，错误码: {ret}")

# 断开机器人连接
cps.HRIF_DisConnect(0)
