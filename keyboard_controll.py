import time
import math
import numpy as np
from dazu.CPS import CPSClient
import yaml
from scipy.spatial.transform import Rotation as R
from collections import deque
import socket

import cv2
def rpy_to_transformation_matrix(x, y, z, roll, pitch, yaw):
    # Create rotation matrix from RPY angles
    r = R.from_euler('xyz', [roll, pitch, yaw], degrees=True)  # Specify the sequence of axes 'xyz'
    rotation_matrix = r.as_matrix()

    # Create a 4x4 transformation matrix
    transformation_matrix = np.eye(4)  # Start with identity matrix

    # Set the rotation part (3x3) of the transformation matrix
    transformation_matrix[:3, :3] = rotation_matrix

    # Set the translation part (position) in the last column
    transformation_matrix[:3, 3] = [x, y, z]

    return transformation_matrix


# Function to convert a 4x4 transformation matrix to position and RPY
def transformation_matrix_to_rpy(matrix):
    # Extract the translation (x, y, z) from the last column of the matrix
    translation = matrix[:3, 3]
    x, y, z = translation

    # Extract the rotation matrix (top-left 3x3 part of the transformation matrix)
    rotation_matrix = matrix[:3, :3]

    # Convert the rotation matrix to RPY (roll, pitch, yaw) in radians
    r = R.from_matrix(rotation_matrix)
    roll, pitch, yaw = r.as_euler('xyz', degrees=True)

    return x, y, z, roll, pitch, yaw


def update_pose(current_pose, x, y, z, roll, pitch, yaw):
    # Extract the current position and rotation (RPY) from the current pose
    current_position = current_pose[:3]  # Assuming current_pose = [x, y, z, roll, pitch, yaw]
    current_rotation = current_pose[3:]

    # Update translation (position)
    updated_position = np.array(current_position) + np.array([x, y, z])

    # Create the rotation from RPY (roll, pitch, yaw)
    new_rotation = R.from_euler('xyz', [roll, pitch, yaw], degrees=True)

    # Convert the current rotation (RPY) to a Rotation object
    current_rotation_r = R.from_euler('xyz', current_rotation, degrees=True)

    # Combine the rotations (multiplying quaternion or matrix form)
    updated_rotation = current_rotation_r * new_rotation

    # Extract updated RPY from the new combined rotation
    updated_rpy = updated_rotation.as_euler('xyz', degrees=True)

    # Return the updated pose (position + RPY)
    updated_pose = np.concatenate([updated_position, updated_rpy])

    return updated_pose


class RobotController:
    def __init__(self, box_id=0, rbt_id=0,
                 step_size=100, rotation_step_size=0.1 * 10):
        """
        初始化机器人控制器
        :param step_size: 控制机器人每次移动的步进量（默认值为1）
        :param rotation_step_size: 控制机器人每次旋转的步进量（默认值为5）
        """
        self.box_id = box_id
        self.rbt_id = rbt_id

        self.client = CPSClient()
        self.step_size = step_size  # 步进量
        self.rotation_step_size = rotation_step_size  # 旋转步进量

        # 连接到电箱和控制器
        self.client.HRIF_Connect(self.box_id, '192.168.11.7', 10003)
        self.client.HRIF_Connect2Controller(self.box_id)

        # 获取当前位置
        self.current_pose = self.client.read_pos()
        print(f"Initial Current Pose: {self.current_pose}")

    def move_arm(self, pose, dServoTime):
        """
        控制机械臂移动到指定的pose，pose包含位置和姿态的6个参数（x, y, z, Rx, Ry, Rz）。
        """
        ucs = [0, 0, 0, 0, 0, 0]  # 运动坐标系的占位符
        tcp = [0, 0, 0, 0, 0, 0]  # 末端执行器坐标系的占位符
        res = self.client.HRIF_PushServoP(self.box_id, self.rbt_id, pose, ucs, tcp)
        print(res)
        time.sleep(0.001)  # 延迟，防止命令重叠

    def move_arm_using_sock(self, sock, speeds, accelerations, servotime, id=0):
        cmd = "SpeedL"
        print(speeds)
        self.sendCMD(sock, cmd, id, speeds, accelerations,run_time=servotime)
        return

    def connectDZController(self, ip, port=8055):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((ip, port))
            return (True, sock)
        except Exception as e:
            sock.close()
            return (False, None)

    # 断开与机器人控制器的连接
    def disconnectETController(self, sock):
        if sock:
            sock.close()
        return None

    def sendCMD(self, sock, cmd, id, speeds, accelerations, run_time):
        sendStr = f"{cmd},{id},{','.join(map(str, speeds))},{','.join(map(str, accelerations))},{run_time},;"

        try:
            sock.sendall(bytes(sendStr, "utf-8"))
            print(f"sendstr:{sendStr}")
        except Exception as e:
            print(e)
            return (False, None, None)

    def control_arm_with_cv2(self):
        """
        使用 OpenCV 显示图像窗口并监听键盘输入来控制机械臂
        """
        # 初始化坐标

        # 创建窗口
        # cv2.namedWindow('Robot Control')
        dServoTime = 0.07
        dLookaheadTime = 0.08

        # plt.ion()  # turning interactive mode on
        #
        # # preparing the data
        # x_data = deque(maxlen=200)
        # time_data = deque(maxlen=200)
        # initial_time = time.time()
        #
        # # plotting the first frame
        # graph = plt.plot(time_data,x_data)[0]
        # plt.ylim(0, 10)
        # plt.pause(1)

        _, sock = self.connectDZController("192.168.11.7", 10003)

        while True:
            # 显示图像（简单的文本提示）
            img = 255 * np.ones(shape=[620, 900, 3], dtype=np.uint8)  # 创建一个白色背景图像
            cv2.putText(img, "Use Arrow Keys to control the robot", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(img, f"Step Size: {self.step_size}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(img, f"Rotation Step Size: {self.rotation_step_size}", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 0, 0), 2)
            cv2.putText(img, "W: Move Forward (Increase X)", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "S: Move Backward (Decrease X)", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "A: Move Left (Decrease Y)", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "D: Move Right (Increase Y)", (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "Q: Move Up (Increase Z)", (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "E: Move Down (Decrease Z)", (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "I: Rotate Counter-Clockwise (Increase Rx)", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 0, 0), 2)
            cv2.putText(img, "K: Rotate Clockwise (Decrease Rx)", (50, 550), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0),
                        2)
            cv2.putText(img, "Press ESC to exit", (50, 600), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

            # 显示图像
            cv2.imshow('Robot Control', img)
            x, y, z, rx, ry, rz = 0, 0, 0, 0, 0, 0

            # 按键事件处理
            key = cv2.waitKey(100) & 0xFF  # 获取按键的ASCII码
            if key == 27:  # 按下ESC退出
                break
            elif key == ord('w'):
                x += self.step_size  # 移动前进（增加X坐标）
            elif key == ord('s'):
                x -= self.step_size  # 移动后退（减少X坐标）
            elif key == ord('a'):
                y -= self.step_size  # 向左移动（减少Y坐标）
            elif key == ord('d'):
                y += self.step_size  # 向右移动（增加Y坐标）
            elif key == ord('q'):
                z += self.step_size  # 向上移动（增加Z坐标）
            elif key == ord('e'):
                z -= self.step_size  # 向下移动（减少Z坐标）
            elif key == ord('i'):
                rx += self.rotation_step_size  # 绕X轴顺时针旋转（增加Rx）
            elif key == ord('k'):
                rx -= self.rotation_step_size  # 绕X轴逆时针旋转（减少Rx）
            elif key == ord('j'):
                ry += self.rotation_step_size  # 绕Y轴顺时针旋转（增加Ry）
            elif key == ord('l'):
                ry -= self.rotation_step_size  # 绕Y轴逆时针旋转（减少Ry）
            elif key == ord('u'):
                rz += self.rotation_step_size  # 绕Z轴顺时针旋转（增加Rz）
            elif key == ord('o'):
                rz -= self.rotation_step_size  # 绕Z轴逆时针旋转（减少Rz）
            elif key == ord('m'):
                break

            self.current_pose = self.client.read_pos()
            roll, pitch, yaw = self.current_pose[3], self.current_pose[4], self.current_pose[5]
            base2end_rpy_matrix = R.from_euler('xyz', [roll, pitch, yaw], degrees=True).as_matrix()
            transformation_matrix_diff_rpy = R.from_euler('xyz', [rx, ry, rz], degrees=True).as_matrix()
            xyz_diff = np.array([x, y, z]) @ np.linalg.inv(base2end_rpy_matrix)
            rpy = R.from_matrix(base2end_rpy_matrix @ transformation_matrix_diff_rpy).as_euler("xyz", degrees=True)
            pose = np.array([self.current_pose[0] + xyz_diff[0],
                             self.current_pose[1] + xyz_diff[1],
                             self.current_pose[2] + xyz_diff[2],
                             rpy[0],
                             rpy[1],
                             rpy[2]
                             ], dtype=float)
            rpy0 = R.from_matrix(transformation_matrix_diff_rpy).as_euler("xyz", degrees=True)
            speed = xyz_diff + rpy0
            acc = [1, 1]
            dServoTime = 0.1
            self.move_arm_using_sock(sock, speed, acc, dServoTime)

        # 销毁窗口
        # with open("x_data.txt", 'a') as file:
        #     file.write(" ".join(map(str, x_data)) + "\n")
        # with open("time_data.txt", 'a') as file:
        #     file.write(" ".join(map(str, time_data)) + "\n")
        cv2.destroyAllWindows()
        # 关闭图形窗口时的清理操作


    def control_arm_with_sock(self):
        """
        使用 OpenCV 显示图像窗口并监听键盘输入来控制机械臂
        """

        _, sock = self.connectDZController("192.168.11.7", 10003)

        while True:
            # 显示图像（简单的文本提示）
            img = 255 * np.ones(shape=[620, 900, 3], dtype=np.uint8)  # 创建一个白色背景图像
            cv2.putText(img, "Use Arrow Keys to control the robot", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(img, f"Step Size: {self.step_size}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.putText(img, f"Rotation Step Size: {self.rotation_step_size}", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 0, 0), 2)
            cv2.putText(img, "W: Move Forward (Increase X)", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "S: Move Backward (Decrease X)", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "A: Move Left (Decrease Y)", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "D: Move Right (Increase Y)", (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "Q: Move Up (Increase Z)", (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "E: Move Down (Decrease Z)", (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            cv2.putText(img, "I: Rotate Counter-Clockwise (Increase Rx)", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 0, 0), 2)
            cv2.putText(img, "K: Rotate Clockwise (Decrease Rx)", (50, 550), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0),
                        2)
            cv2.putText(img, "Press ESC to exit", (50, 600), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

            # 显示图像
            cv2.imshow('Robot Control', img)
            speed = [0, 0, 0, 0, 0, 0]
            x, y, z, rx, ry, rz = 0, 0, 0, 0, 0, 0

            # 按键事件处理
            key = cv2.waitKey(1) & 0xFF  # 获取按键的ASCII码
            if key == 27:  # 按下ESC退出
                break
            elif key == ord('w'):
                speed[0] = self.step_size
            elif key == ord('s'):
                speed[0] = self.step_size
            elif key == ord('a'):
                speed[1] = self.step_size
            elif key == ord('d'):
                speed[1] = self.step_size
            elif key == ord('q'):
                speed[2] = self.step_size
            elif key == ord('e'):
                speed[2] = self.step_size
            elif key == ord('i'):
                speed[3] = self.rotation_step_size
            elif key == ord('k'):
                speed[3] = self.rotation_step_size
            elif key == ord('j'):
                speed[4] = self.rotation_step_size
            elif key == ord('l'):
                speed[4] = self.rotation_step_size
            elif key == ord('u'):
                speed[5] = self.rotation_step_size
            elif key == ord('o'):
                speed[5] = self.rotation_step_size
            acc = [1, 1]
            self.current_pose = self.client.read_pos()
            dServoTime = 0.01
            self.move_arm_using_sock(sock, speed, acc, dServoTime)


        cv2.destroyAllWindows()
        plt.ioff()  # 关闭交互模式
        plt.show()


def main():
    controller = RobotController()
    controller.control_arm_with_sock()  # 启动cv2控制


# 启动程序
if __name__ == "__main__":
    main()
