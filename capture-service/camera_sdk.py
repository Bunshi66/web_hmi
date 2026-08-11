"""
Обёртка над Hikrobot MvCameraSDK.
"""
import sys
import os
import time
from ctypes import c_ubyte, c_void_p, byref, cast, POINTER
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), 'MvImport'))

from MvImport.MvCameraControl_class import MvCamera
from MvImport.CameraParams_header import (
    MV_CC_DEVICE_INFO_LIST,
    MV_CC_DEVICE_INFO,
    MV_FRAME_OUT,
    MV_FRAME_OUT_INFO_EX,
    MVCC_FLOATVALUE,
)
from MvImport.MvErrorDefine_const import MV_OK
from MvImport.PixelType_header import PixelType_Gvsp_BGR8_Packed

# Константы интерфейсов
MV_GIGE_DEVICE = 0x00000001
MV_USB_DEVICE = 0x00000002


class HikrobotCamera:
    """Управление камерой Hikrobot через MvCameraSDK."""

    def __init__(self):
        self._cam = MvCamera()
        self._connected = False
        self._grabbing = False

    def connect(self, ip: str = None) -> bool:
        """Найти камеру и подключиться."""
        if self._connected:
            print("[INFO] Already connected.")
            return True
        try:
            ret = MvCamera.MV_CC_Initialize()
            if ret != MV_OK:
                print(f"[ERROR] Initialize failed: 0x{ret:08X}")
                return False

            device_list = MV_CC_DEVICE_INFO_LIST()
            ret = MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE, device_list)
            if ret != MV_OK or device_list.nDeviceNum == 0:
                print(f"[ERROR] No cameras found")
                return False

            print(f"[INFO] Found {device_list.nDeviceNum} device(s)")

            st_device = cast(
                device_list.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)
            ).contents

            ret = self._cam.MV_CC_CreateHandle(st_device)
            if ret != MV_OK:
                print(f"[ERROR] CreateHandle failed: 0x{ret:08X}")
                return False

            ret = self._cam.MV_CC_OpenDevice()
            if ret != MV_OK:
                print(f"[ERROR] OpenDevice failed: 0x{ret:08X}")
                return False

            # Устанавливаем режим съёмки
            self._cam.MV_CC_SetEnumValueByString("AcquisitionMode", "Continuous")

            self._connected = True
            print(f"[INFO] Connected to camera")
            return True

        except Exception as e:
            print(f"[ERROR] connect: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start_grabbing(self) -> bool:
        """Начать захват."""
        if not self._connected:
            return False
        ret = self._cam.MV_CC_StartGrabbing()
        if ret != MV_OK:
            print(f"[ERROR] StartGrabbing failed: 0x{ret:08X}")
            return False
        self._grabbing = True
        print("[INFO] Grabbing started")
        return True

    def stop_grabbing(self) -> bool:
        """Остановить захват."""
        if not self._grabbing:
            return True
        ret = self._cam.MV_CC_StopGrabbing()
        self._grabbing = False
        print("[INFO] Grabbing stopped")
        return ret == MV_OK

    def set_exposure(self, exposure_time_us: float) -> bool:
        """Установить экспозицию (в микросекундах)"""
        if not self._connected:
            return False
        # Отключаем авто-экспозицию перед установкой
        self._cam.MV_CC_SetEnumValueByString("ExposureAuto", "Off")
        ret = self._cam.MV_CC_SetFloatValue("ExposureTime", float(exposure_time_us))
        if ret != MV_OK:
            print(f"[ERROR] Failed to set ExposureTime: 0x{ret:08X}")
            return False
        return True

    def set_gain(self, gain: float) -> bool:
        """Установить усиление (Gain)"""
        if not self._connected:
            return False
        # Отключаем авто-усиление перед установкой
        self._cam.MV_CC_SetEnumValueByString("GainAuto", "Off")
        ret = self._cam.MV_CC_SetFloatValue("Gain", float(gain))
        if ret != MV_OK:
            print(f"[ERROR] Failed to set Gain: 0x{ret:08X}")
            return False
        return True

    def get_temperature(self) -> float:
        """Получить температуру камеры (с перебором вариантов)."""
        if not self._connected:
            return 0.0

        stFloatValue = MVCC_FLOATVALUE()

        # Вариант 1: Стандартный DeviceTemperature (как Float)
        ret = self._cam.MV_CC_GetFloatValue("DeviceTemperature", stFloatValue)
        if ret == MV_OK:
            return stFloatValue.fCurValue

        # Вариант 2: Возможно, нужно сначала выбрать сенсор через Selector
        ret_sel = self._cam.MV_CC_SetEnumValueByString("DeviceTemperatureSelector", "Sensor")
        if ret_sel == MV_OK:
            ret = self._cam.MV_CC_GetFloatValue("DeviceTemperature", stFloatValue)
            if ret == MV_OK:
                return stFloatValue.fCurValue

        # Вариант 3: На старых моделях это узел "Temperature" (как Float)
        ret = self._cam.MV_CC_GetFloatValue("Temperature", stFloatValue)
        if ret == MV_OK:
            return stFloatValue.fCurValue

        # Если ничего не помогло — чтобы не спамить в логи каждые 33 мс, 
        # возвращаем 0.0 молча.
        return 0.0


    def trigger_defect(self) -> bool:
        """Аппаратный триггер: Line 1, Software"""
        if not self._connected:
            return False
        
        # Try to use standard UserOutput for generic GPIO if LineTriggerSoftware fails
        try:
            self._cam.MV_CC_SetEnumValueByString("LineSelector", "Line1")
            self._cam.MV_CC_SetEnumValueByString("LineMode", "Strobe")
        except:
            pass # Ignore if not supported

        ret = self._cam.MV_CC_SetCommandValue("LineTriggerSoftware")
        if ret != MV_OK:
            # Fallback for cameras that don't support LineTriggerSoftware
            ret2 = self._cam.MV_CC_SetCommandValue("TriggerSoftware")
            if ret2 != MV_OK:
                print(f"[WARN] Trigger defect might not be supported. Error codes: 0x{ret:08X}, 0x{ret2:08X}")
                return False
                
        print("[INFO] Defect triggered via GPIO")
        return True

    def configure_io_output(self, line_name: str = "Line2", output_name: str = "UserOutput1") -> bool:
        """Настраивает физическую линию (IO) камеры как программно управляемый выход."""
        if not self._connected:
            return False
            
        try:
            self._cam.MV_CC_SetEnumValueByString("LineSelector", line_name)
            self._cam.MV_CC_SetEnumValueByString("LineMode", "Strobe") 
            self._cam.MV_CC_SetEnumValueByString("LineSource", output_name)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to configure IO output: {e}")
            return False

    def set_io_value(self, state: bool, output_name: str = "UserOutput1") -> bool:
        """Устанавливает логическое состояние (Вкл/Выкл) на настроенном выходе."""
        if not self._connected:
            return False
            
        ret_sel = self._cam.MV_CC_SetEnumValueByString("UserOutputSelector", output_name)
        if ret_sel != MV_OK:
            print(f"[ERROR] Failed to select {output_name}: 0x{ret_sel:08X}")
            return False
            
        ret_val = self._cam.MV_CC_SetBoolValue("UserOutputValue", state)
        if ret_val != MV_OK:
            print(f"[ERROR] Failed to set UserOutputValue to {state}: 0x{ret_val:08X}")
            return False
            
        print(f"[INFO] Set {output_name} to {state}")
        return True

    def get_frame(self, timeout_ms: int = 1000) -> np.ndarray | None:
        """Получить кадр как numpy array (BGR)."""
        if not self._grabbing:
            return None

        frame = MV_FRAME_OUT()
        ret = self._cam.MV_CC_GetImageBuffer(frame, timeout_ms)
        if ret != MV_OK:
            return None

        try:
            data_ptr = frame.pBufAddr
            data_len = frame.stFrameInfo.nFrameLen
            pixel_type = frame.stFrameInfo.enPixelType

            # Копируем данные через from_address (надёжный способ)
            img_data = (c_ubyte * data_len).from_address(
                cast(data_ptr, c_void_p).value
            )
            img_np = np.frombuffer(img_data, dtype=np.uint8)

            if pixel_type == PixelType_Gvsp_BGR8_Packed:
                img = img_np.reshape(
                    frame.stFrameInfo.nHeight,
                    frame.stFrameInfo.nWidth,
                    3
                ).copy()
                return img
            else:
                print(f"[WARN] Unsupported pixel type: 0x{pixel_type:08X}")
                # Пробуем как моно
                return img_np.reshape(
                    frame.stFrameInfo.nHeight,
                    frame.stFrameInfo.nWidth
                ).copy()

        finally:
            self._cam.MV_CC_FreeImageBuffer(frame)

    def release(self):
        """Освободить ресурсы."""
        if self._grabbing:
            self.stop_grabbing()
        if self._connected:
            self._cam.MV_CC_CloseDevice()
            self._cam.MV_CC_DestroyHandle()
            MvCamera.MV_CC_Finalize()
            self._connected = False
            print("[INFO] Device closed")


# ─── Тестовый запуск ───────────────────────────────────────

if __name__ == "__main__":
    import cv2

    cam = HikrobotCamera()

    print("Connecting...")
    if not cam.connect():
        print("Failed to connect.")
        exit(1)

    print("Starting grab...")
    if not cam.start_grabbing():
        cam.release()
        exit(1)

    print("Capturing 10 frames...")
    for i in range(10):
        frame = cam.get_frame(timeout_ms=1000)
        if frame is not None:
            print(f"  Frame {i + 1}: {frame.shape}, mean={frame.mean():.1f}")
            cv2.imwrite(f"test_frame_{i:03d}.jpg", frame)
        else:
            print(f"  Frame {i + 1}: timeout")
        time.sleep(0.1)

    cam.release()
    print("Done.")