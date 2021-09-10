# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

face_models = [
('.\\face_recognition_models\\models\\dlib_face_recognition_resnet_model_v1.dat', '.\\face_recognition_models\\models'),
('.\\face_recognition_models\\models\\mmod_human_face_detector.dat', '.\\face_recognition_models\\models'),
('.\\face_recognition_models\\models\\shape_predictor_5_face_landmarks.dat', '.\\face_recognition_models\\models'),
('.\\face_recognition_models\\models\\shape_predictor_68_face_landmarks.dat', '.\\face_recognition_models\\models'),
]

a = Analysis(['main.py'],
             pathex=['C:/Users/marcos.filho/PycharmProjects/FaceDetectionUI'],
             binaries=face_models,
             datas=[
                ('material/haarcascade_frontalface_default.xml','material'),
                ('processing/model_01_human_category.h5','processing'),
                ('icon/faceicon.ico','icon')
             ],
             hiddenimports=["babel.numbers"],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False
            )

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
    )

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Detector Facial',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon='icon/faceicon.ico'
    )
