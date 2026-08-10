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