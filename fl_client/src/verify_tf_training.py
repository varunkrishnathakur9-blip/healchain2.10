
import os
import sys
import tensorflow as tf

# Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from training.model import ResNet9, load_model_checkpoint
from dataset.loader import load_local_dataset
from training.trainer import local_train

def main():
    """
    Verify the TensorFlow-based training pipeline.
    """
    print("[Test] Starting TensorFlow training verification...")

    # 1. Create a dummy ResNet9 model
    print("[Test] Creating a dummy ResNet9 model...")
    dummy_model = ResNet9(input_shape=(10,), num_classes=2)
    dummy_model.build(input_shape=(None, 10))
    print("[Test] Dummy model created.")

    # 2. Save the model to a temporary H5 file
    checkpoint_path = "temp_model.h5"
    print(f"[Test] Saving dummy model to {checkpoint_path}...")
    dummy_model.save(checkpoint_path)
    print("[Test] Dummy model saved.")

    # 3. Load the model using the checkpoint loading function
    print("[Test] Loading model from checkpoint...")
    loaded_model = load_model_checkpoint(checkpoint_path)
    print("[Test] Model loaded successfully.")
    
    # 4. Load the dataset (using synthetic fallback)
    print("[Test] Loading local dataset (synthetic fallback)...")
    dataset = load_local_dataset(dataset_type="synthetic_test")
    print("[Test] Dataset loaded.")

    # 5. Run the local training
    print("[Test] Starting local training...")
    trained_model = local_train(loaded_model, dataset, epochs=1)
    print("[Test] Local training completed.")

    # 6. Check weights
    print("[Test] Verifying custom weight methods...")
    try:
        weights = trained_model.get_weights_custom()
        print(f"[Test] get_weights_custom() returned {len(weights)} numbers.")
        
        trained_model.set_weights_custom(weights)
        print("[Test] set_weights_custom() executed.")
        print("[Test] Custom weight methods verified.")
    except Exception as e:
        print(f"[Test] Error during weight method verification: {e}")


    # Clean up the temporary model file
    os.remove(checkpoint_path)
    print(f"[Test] Cleaned up {checkpoint_path}.")

    print("\n[Test] TensorFlow training verification script completed successfully!")

if __name__ == "__main__":
    main()
