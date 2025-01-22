import cv2
import numpy as np
from dazu.CPS import CPSClient


class RobotController:
    def __init__(self, box_id=0, rbt_id=0):
        self.box_id = box_id
        self.rbt_id = rbt_id
        self.client = CPSClient()

        # 连接到电箱和控制器
        self.client.HRIF_Connect(self.box_id, '192.168.11.7', 10003)
        self.client.HRIF_Connect2Controller(self.box_id)

    def HRIF_LongJogL(self, boxID, rbtID, pcsId, derection, state):
        # 构建命令字符串
        command = f'LongJogL,{rbtID},{pcsId},{derection},{state};'
        print(f"Sending command: {command}")
        # 发送命令
        # 这里应有实际的命令发送代码，例如:
        # response = self.client.sendAndRecv(command)
        # return response  # 假设这个方法返回错误码

    def control_arm_with_cv2(self):
        cv2.namedWindow('Robot Control')

        # 定义方向和坐标轴映射
        axis_direction = {
            ord('w'): (1, 1),  # X轴，正方向
            ord('s'): (1, 0),  # X轴，负方向
            ord('d'): (2, 1),  # Y轴，正方向
            ord('a'): (2, 0),  # Y轴，负方向
            ord('q'): (3, 1),  # Z轴，正方向
            ord('e'): (3, 0)  # Z轴，负方向
        }

        while True:
            img = 255 * np.ones(shape=[300, 500, 3], dtype=np.uint8)  # 创建一个白色背景图像
            cv2.putText(img, "Use WASDQE to control the robot", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.imshow('Robot Control', img)

            key = cv2.waitKey(1) & 0xFF  # 获取按键的ASCII码
            if key == 27:  # 按下ESC退出
                break
            elif key in axis_direction:
                axis, direction = axis_direction[key]
                # 调用HRIF_LongJogL启动或调整移动
                self.client.HRIF_LongJogL(self.box_id, self.rbt_id, axis, direction, 1)  # 1表示开启
            elif key == ord('r'):  # 假设按'r'停止所有运动
                for axis in range(1, 4):  # 停止所有轴的运动
                    self.client.HRIF_LongJogL(self.box_id, self.rbt_id, axis, 0, 0)  # 0为方向（不用），0为停止状态

        cv2.destroyAllWindows()


def main():
    controller = RobotController()
    controller.control_arm_with_cv2()


if __name__ == "__main__":
    main()
