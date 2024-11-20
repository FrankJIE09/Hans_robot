import serial
import struct
import time


def parse_data(response):
    """
    解析设备响应数据，按照文档中的转换方式进行转换。
    """
    if len(response) < 5:  # 最小响应长度
        print("无效或空的响应数据")
        return None

    # 提取数据并转换
    data_values = []
    for i in range(3, len(response) - 2, 4):  # 跳过头部和CRC部分
        data_segment = response[i:i + 4]

        # 符号位
        sign = data_segment[0]
        is_negative = sign == 1  # 如果符号位为1，表示负数

        # 提取高字节和低字节
        high_byte = data_segment[2]  # 第3字节
        low_byte = data_segment[3]  # 第4字节

        # 转换为整数值
        value = (high_byte << 8) + low_byte  # 高字节乘以256加低字节
        if is_negative:
            value = -value  # 如果符号位为1，将值设为负数

        # 转换为毫米单位（如果需要）
        value_mm = value / 1000.0  # 根据需要调整转换系数
        data_values.append(value_mm)

    return data_values


def read_average_data(port, baudrate=38400, address=128, data_count=8):
    """
    读取数据3次并计算每组数据的平均值
    """
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=1)
        all_values = [[] for _ in range(4)]  # 存储每组数据的列表

        for _ in range(3):  # 循环读取3次
            # 构建读取数据的命令帧
            data = struct.pack('>HH', 0, data_count)  # 起始地址0和数据数量
            command = build_command(address, 0x03, data)  # 假设您有 build_command 方法
            ser.write(command)
            response = ser.read(256)  # 读取设备返回的数据

            # 解析和存储数据
            if response:
                parsed_data = parse_data(response)
                if parsed_data and len(parsed_data) == 4:  # 确认解析到4组数据
                    for i in range(4):
                        all_values[i].append(parsed_data[i])  # 将每组数据添加到对应的列表
            else:
                print("无响应，重试中...")
            time.sleep(0.1)  # 每次读取之间的延迟

        # 计算每组数据的平均值
        average_values = [sum(group) / len(group) if group else None for group in all_values]
        return average_values

    except serial.SerialException as e:
        print(f"串口错误: {e}")
        return None
    finally:
        ser.close()


def build_command(address, function_code, data):
    """
    构建Modbus命令帧
    """
    frame = struct.pack('B', address) + struct.pack('B', function_code) + data
    crc = calculate_crc(frame)
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    return frame + struct.pack('BB', crc_low, crc_high)


def calculate_crc(data):
    """
    计算16位CRC校验码
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


# 示例调用
if __name__ == "__main__":
    avg_values = read_average_data(port='COM3')
    if avg_values is not None:
        print("每组的平均值为:")
        for i, avg in enumerate(avg_values):
            print(f"组 {i + 1}: {avg:.3f} mm")
