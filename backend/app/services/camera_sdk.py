"""
Обёртка над Hikrobot MvCameraSDK.
"""
import sys
import os
import time
import logging
from ctypes import c_ubyte, c_void_p, byref, cast, POINTER
import numpy as np
import cv2

logger = logging.getLogger("camera_sdk")
logger.setLevel(logging.INFO)
# We assume the parent app configures handlers, but if run standalone, we add one
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

sys.path.append(os.path.join(os.path.dirname(__file__), 'MvImport'))

from MvCameraControl_class import MvCamera
from CameraParams_header import (
    MV_CC_DEVICE_INFO_LIST,
    MV_INTERFACE_INFO_LIST,
    MV_CC_DEVICE_INFO,
    MV_FRAME_OUT,
    MV_FRAME_OUT_INFO_EX,
    MVCC_FLOATVALUE,
)
from MvErrorDefine_const import MV_OK
from PixelType_header import PixelType_Gvsp_BGR8_Packed

# Константы интерфейсов
MV_GIGE_DEVICE = 0x00000001
MV_USB_DEVICE = 0x00000002


class HikrobotCamera:
    """Управление камерой Hikrobot через MvCameraSDK."""

    def __init__(self):
        self._cam = MvCamera()
        self._connected = False
        self._grabbing = False

    def is_alive(self) -> bool:
        """Проверить физическое подключение камеры."""
        if getattr(self, '_cam', None) and hasattr(self._cam, 'MV_CC_IsDeviceConnected'):
            try:
                return self._cam.MV_CC_IsDeviceConnected()
            except Exception:
                return False
        return self._connected

    def connect(self, ip: str = None) -> bool:
        """Найти камеру и подключиться."""
        if self._connected and self.is_alive():
            logger.info("Already connected.")
            return True
        try:
            ret = MvCamera.MV_CC_Initialize()
            if ret != MV_OK:
                logger.error(f"Initialize failed: 0x{ret:08X}")
                return False

            # Try GenTL Enum
            from CameraParams_header import MV_GENTL_IF_INFO_LIST, MV_GENTL_DEV_INFO_LIST, MV_GENTL_IF_INFO, MV_GENTL_DEV_INFO

            gentl_if_list = MV_GENTL_IF_INFO_LIST()
            ret_gentl = MvCamera.MV_CC_EnumInterfacesByGenTL(gentl_if_list, "/opt/MVS/lib/64/MvProducerGEV.cti")
            logger.debug(f"GenTL EnumInterfaces: 0x{ret_gentl:08X}, num: {gentl_if_list.nInterfaceNum}")

            if gentl_if_list.nInterfaceNum > 0:
                for i in range(gentl_if_list.nInterfaceNum):
                    if_info_ptr = cast(gentl_if_list.pIFInfo[i], POINTER(MV_GENTL_IF_INFO))
                    if_info = cast(gentl_if_list.pIFInfo[i], POINTER(MV_GENTL_IF_INFO)).contents
                    if_id = bytes(if_info.chInterfaceID).decode('ascii', errors='ignore').rstrip('\x00')
                    gentl_dev_list = MV_GENTL_DEV_INFO_LIST()
                    ret_dev = MvCamera.MV_CC_EnumDevicesByGenTL(if_info_ptr, gentl_dev_list)
                    logger.debug(f"GenTL EnumDevices IF[{i}] ({if_id}): 0x{ret_dev:08X}, num: {gentl_dev_list.nDeviceNum}")
                    
                    if ret_dev == MV_OK and gentl_dev_list.nDeviceNum > 0:
                        st_device = cast(gentl_dev_list.pDeviceInfo[0], POINTER(MV_GENTL_DEV_INFO)).contents
                        ret_create = self._cam.MV_CC_CreateHandleByGenTL(st_device)
                        if ret_create == MV_OK:
                            logger.info("Created handle via GenTL!")
                            ret_open = self._cam.MV_CC_OpenDevice()
                            if ret_open == MV_OK:
                                self._cam.MV_CC_SetEnumValueByString("AcquisitionMode", "Continuous")
                                self._cam.MV_CC_SetEnumValueByString("ExposureAuto", "Continuous")
                                self._cam.MV_CC_SetEnumValueByString("GainAuto", "Continuous")
                                self._cam.MV_CC_SetIntValue("GevHeartbeatTimeout", 10000)
                                self._connected = True
                                logger.info("Connected to camera via GenTL")
                                return True
                            else:
                                logger.error(f"OpenDevice (GenTL) failed: 0x{ret_open:08X}")
                                self._cam.MV_CC_DestroyHandle()
                        else:
                            logger.error(f"CreateHandleByGenTL failed: 0x{ret_create:08X}")

            device_list = MV_CC_DEVICE_INFO_LIST()
            ret = MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE, device_list)
            if ret != MV_OK or device_list.nDeviceNum == 0:
                logger.error(f"No cameras found (ret=0x{ret:08X}, nDeviceNum={device_list.nDeviceNum})")
                return False

            logger.info(f"Found {device_list.nDeviceNum} device(s) via standard Enum")

            for i in range(device_list.nDeviceNum):
                st_device = cast(device_list.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
                
                ret = self._cam.MV_CC_CreateHandle(st_device)
                if ret != MV_OK:
                    logger.error(f"CreateHandle failed for device {i}: 0x{ret:08X}")
                    continue

                ret = self._cam.MV_CC_OpenDevice()
                if ret != MV_OK:
                    logger.error(f"OpenDevice failed for device {i}: 0x{ret:08X}")
                    self._cam.MV_CC_DestroyHandle()
                    continue

                self._cam.MV_CC_SetEnumValueByString("AcquisitionMode", "Continuous")
                self._cam.MV_CC_SetEnumValueByString("ExposureAuto", "Continuous")
                self._cam.MV_CC_SetEnumValueByString("GainAuto", "Continuous")
                self._cam.MV_CC_SetIntValue("GevHeartbeatTimeout", 10000)
                self._connected = True
                logger.info(f"Connected to camera (Standard) on device {i}")
                return True

            logger.error("Failed to connect to any of the enumerated devices.")
            return False

        except Exception as e:
            logger.exception(f"connect exception: {e}")
            return False

    def start_grabbing(self) -> bool:
        """Начать захват."""
        if not self._connected:
            return False
        ret = self._cam.MV_CC_StartGrabbing()
        if ret != MV_OK:
            logger.error(f"StartGrabbing failed: 0x{ret:08X}")
            return False
        self._grabbing = True
        logger.info("Grabbing started")
        return True

    def stop_grabbing(self) -> bool:
        """Остановить захват."""
        if not self._grabbing:
            return True
        ret = self._cam.MV_CC_StopGrabbing()
        self._grabbing = False
        logger.info("Grabbing stopped")
        return ret == MV_OK

    def set_exposure(self, exposure_time_us: float) -> bool:
        """Установить экспозицию (в микросекундах)"""
        if not self._connected:
            return False
        # Отключаем авто-экспозицию перед установкой
        self._cam.MV_CC_SetEnumValueByString("ExposureAuto", "Off")
        ret = self._cam.MV_CC_SetFloatValue("ExposureTime", float(exposure_time_us))
        if ret != MV_OK:
            logger.error(f"Failed to set ExposureTime: 0x{ret:08X}")
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
            logger.error(f"Failed to set Gain: 0x{ret:08X}")
            return False
        return True

    def get_temperature(self) -> float:
        """Получить температуру камеры (с перебором вариантов)."""
        if not self._connected:
            return 0.0

        if not hasattr(self, '_debug_temp_count'):
            self._debug_temp_count = 0
            
        stFloatValue = MVCC_FLOATVALUE()
        should_print = self._debug_temp_count < 2
        if should_print:
            logger.debug("Attempting to read temperature...")

        # Вариант 1: Стандартный DeviceTemperature (как Float)
        ret1 = self._cam.MV_CC_GetFloatValue("DeviceTemperature", stFloatValue)
        if ret1 == MV_OK:
            return stFloatValue.fCurValue
        elif should_print:
            logger.debug(f"Variant 1 (DeviceTemperature) failed. ret = 0x{ret1:08X}")

        # Вариант 2: Возможно, нужно сначала выбрать сенсор через Selector
        ret_sel = self._cam.MV_CC_SetEnumValueByString("DeviceTemperatureSelector", "Sensor")
        if ret_sel == MV_OK:
            ret2 = self._cam.MV_CC_GetFloatValue("DeviceTemperature", stFloatValue)
            if ret2 == MV_OK:
                return stFloatValue.fCurValue
            elif should_print:
                logger.debug(f"Variant 2 (Selector=Sensor -> DeviceTemperature) failed. ret = 0x{ret2:08X}")
        elif should_print:
            logger.debug(f"Variant 2 (Set DeviceTemperatureSelector) failed. ret = 0x{ret_sel:08X}")

        # Вариант 3: На старых моделях это узел "Temperature" (как Float)
        ret3 = self._cam.MV_CC_GetFloatValue("Temperature", stFloatValue)
        if ret3 == MV_OK:
            return stFloatValue.fCurValue
        elif should_print:
            logger.debug(f"Variant 3 (Temperature) failed. ret = 0x{ret3:08X}")

        if should_print:
            self._debug_temp_count += 1
            logger.debug("All temperature variants failed. Returning 0.0")

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
                logger.warning(f"Trigger defect might not be supported. Error codes: 0x{ret:08X}, 0x{ret2:08X}")
                return False
                
        logger.info("Defect triggered via GPIO")
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
            logger.error(f"Failed to configure IO output: {e}")
            return False

    def set_io_value(self, state: bool, output_name: str = "UserOutput1") -> bool:
        """Устанавливает логическое состояние (Вкл/Выкл) на настроенном выходе."""
        if not self._connected:
            return False
            
        ret_sel = self._cam.MV_CC_SetEnumValueByString("UserOutputSelector", output_name)
        if ret_sel != MV_OK:
            logger.error(f"Failed to select {output_name}: 0x{ret_sel:08X}")
            return False
            
        ret_val = self._cam.MV_CC_SetBoolValue("UserOutputValue", state)
        if ret_val != MV_OK:
            logger.error(f"Failed to set UserOutputValue to {state}: 0x{ret_val:08X}")
            return False
            
        logger.info(f"Set {output_name} to {state}")
        return True

    def get_frame(self, timeout_ms: int = 1000):
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
                expected_size = frame.stFrameInfo.nHeight * frame.stFrameInfo.nWidth * 3
                img_np = img_np[:expected_size]
                img = img_np.reshape(
                    frame.stFrameInfo.nHeight,
                    frame.stFrameInfo.nWidth,
                    3
                ).copy()
                return img
            elif pixel_type == 0x0108000A: # BayerRG8
                expected_size = frame.stFrameInfo.nHeight * frame.stFrameInfo.nWidth
                img_np = img_np[:expected_size]
                raw_bayer = img_np.reshape(
                    frame.stFrameInfo.nHeight,
                    frame.stFrameInfo.nWidth
                ).copy()
                # Convert BayerRG to BGR for OpenCV
                return cv2.cvtColor(raw_bayer, cv2.COLOR_BayerRG2BGR)
            else:
                logger.warning(f"Unsupported pixel type: 0x{pixel_type:08X}")
                # Пробуем как моно
                expected_size = frame.stFrameInfo.nHeight * frame.stFrameInfo.nWidth
                img_np = img_np[:expected_size]
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
            logger.info("Device closed")


# ─── Тестовый запуск ───────────────────────────────────────

if __name__ == "__main__":

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
        else:
            print(f"  Frame {i + 1}: timeout")
        time.sleep(0.1)

    cam.release()
    print("Done.")