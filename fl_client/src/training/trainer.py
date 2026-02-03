import tensorflow as tf

def local_train(model, dataloader, epochs):
    """
    Train a Keras model locally.
    """
    # Assume model is a Keras model
    optimizer = tf.keras.optimizers.SGD(learning_rate=0.01)
    loss_fn = tf.keras.losses.BinaryCrossentropy(from_logits=False)

    model.compile(optimizer=optimizer, loss=loss_fn)

    # Convert dataloader to a tf.data.Dataset if it's not already one
    # This is a generic approach; a more specific one might be needed depending on the dataloader
    if not isinstance(dataloader, tf.data.Dataset):
        # Assuming dataloader yields (x, y) tuples of NumPy arrays
        # This part might need adjustment based on the actual dataloader implementation
        x_samples = [item[0] for item in dataloader]
        y_samples = [item[1] for item in dataloader]
        
        # This is inefficient for large datasets, but works for an unknown dataloader format
        # A better implementation would be to create the tf.data.Dataset in the data loading script
        dataset = tf.data.Dataset.from_tensor_slices((
            tf.concat([tf.constant(x, dtype=tf.float32) for x in x_samples], axis=0),
            tf.concat([tf.constant(y, dtype=tf.int64) for y in y_samples], axis=0)
        ))
        # It's better to define batching at the dataset creation, but we add it here if missing
        # This assumes the original dataloader was batched.
        dataset = dataset.batch(32) # Assuming a default batch size of 32
    else:
        dataset = dataloader

    model.fit(dataset, epochs=epochs, verbose=1)

    return model
