import tensorflow as tf
from tensorflow.keras.layers import (
    Conv2D,
    BatchNormalization,
    ReLU,
    Add,
    GlobalAveragePooling2D,
    Dense,
    Flatten,
    MaxPool2D,
    Input,
)
from tensorflow.keras.models import Model
import numpy as np


def _get_weights(self):
    """For aggregator compatibility"""
    weights = []
    for layer_weights in self.get_weights():
        weights.extend(layer_weights.flatten().tolist())
    return weights


def _set_weights(self, weights):
    """For aggregator compatibility"""
    weight_idx = 0
    new_weights = []
    for layer in self.trainable_variables:
        shape = layer.shape
        size = np.prod(shape)
        w = np.array(weights[weight_idx : weight_idx + size]).reshape(shape)
        new_weights.append(w)
        weight_idx += size
    self.set_weights(new_weights)


class KerasModelWrapper(Model):
    """
    A wrapper to attach get_weights and set_weights methods to a Keras model.
    """

    def __init__(self, model):
        super().__init__()
        self.model = model

    def call(self, inputs, training=False):
        return self.model(inputs, training=training)

    def get_weights_custom(self):
        """For aggregator compatibility"""
        weights = []
        for layer_weights in self.model.get_weights():
            weights.extend(layer_weights.flatten().tolist())
        return weights

    def set_weights_custom(self, weights):
        """For aggregator compatibility"""
        weight_idx = 0
        new_weights = []
        for layer in self.model.trainable_variables:
            shape = layer.shape
            size = np.prod(shape)
            w = np.array(weights[weight_idx : weight_idx + size]).reshape(shape)
            new_weights.append(w)
            weight_idx += size
        self.model.set_weights(new_weights)


def SimpleModel(input_features=4096, output_classes=2):
    """
    Keras implementation of SimpleModel.
    """
    inputs = Input(shape=(input_features,))
    outputs = Dense(output_classes, name="fc")(inputs)
    model = Model(inputs=inputs, outputs=outputs)
    return model


def SimpleCNN(input_shape=(64, 64, 1), num_classes=2):
    """
    Keras implementation of SimpleCNN.
    """
    inputs = Input(shape=input_shape)
    x = Conv2D(32, kernel_size=3, padding="same", activation="relu")(inputs)
    x = MaxPool2D(pool_size=(2, 2))(x)
    x = Conv2D(64, kernel_size=3, padding="same", activation="relu")(x)
    x = MaxPool2D(pool_size=(2, 2))(x)
    x = Flatten()(x)
    x = Dense(128, activation="relu")(x)
    outputs = Dense(num_classes)(x)
    model = Model(inputs=inputs, outputs=outputs)
    return model


def ResidualBlock(x, out_channels, stride=1):
    """
    Keras implementation of a ResNet block.
    """
    in_channels = x.shape[-1]
    shortcut = x

    y = Conv2D(out_channels, kernel_size=3, strides=stride, padding="same", use_bias=False)(x)
    y = BatchNormalization()(y)
    y = ReLU()(y)

    y = Conv2D(out_channels, kernel_size=3, strides=1, padding="same", use_bias=False)(y)
    y = BatchNormalization()(y)

    if stride != 1 or in_channels != out_channels:
        shortcut = Conv2D(out_channels, kernel_size=1, strides=stride, use_bias=False)(x)
        shortcut = BatchNormalization()(shortcut)

    y = Add()([y, shortcut])
    y = ReLU()(y)
    return y


def ResNet9(input_shape=(64, 64, 1), num_classes=2):
    """
    Keras implementation of ResNet9.
    """
    inputs = Input(shape=input_shape)

    x = Conv2D(64, kernel_size=3, strides=1, padding="same", use_bias=False)(inputs)
    x = BatchNormalization()(x)
    x = ReLU()(x)

    x = ResidualBlock(x, 64, stride=2)
    x = ResidualBlock(x, 64, stride=1)
    
    x = ResidualBlock(x, 128, stride=2)
    x = ResidualBlock(x, 128, stride=1)
    
    x = GlobalAveragePooling2D()(x)
    outputs = Dense(num_classes)(x)

    model = Model(inputs=inputs, outputs=outputs)
    return model


def load_model_checkpoint(checkpoint_path: str):
    """
    Load model from TensorFlow/Keras checkpoint.
    Assumes H5 file format.
    """
    print(f"[Model] Loading checkpoint: {checkpoint_path}")
    
    # Load the Keras model
    model = tf.keras.models.load_model(checkpoint_path)
    
    # Wrap the model to attach custom methods
    wrapped_model = KerasModelWrapper(model)

    return wrapped_model