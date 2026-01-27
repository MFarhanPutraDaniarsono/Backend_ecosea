import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ai", "model_pantai.keras")  # atau .h5 sesuai file kamu

try:
    model = tf.keras.models.load_model(
        MODEL_PATH,
        custom_objects={"preprocess_input": preprocess_input},
        safe_mode=False
    )
except TypeError:
    # fallback kalau tf/keras kamu belum support safe_mode param
    model = tf.keras.models.load_model(
        MODEL_PATH,
        custom_objects={"preprocess_input": preprocess_input}
    )

CLASS_NAMES = ["bersih", "kotor"]

def predict_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    preds = model.predict(img_array)[0]
    idx = int(np.argmax(preds))
    conf = float(preds[idx])

    return {
        "label": CLASS_NAMES[idx],
        "confidence": round(conf, 4),
        "probs": {CLASS_NAMES[i]: float(preds[i]) for i in range(len(CLASS_NAMES))}
    }
