import sys
import os
import tensorflow as tf
import numpy as np
import re
from spektral.layers import GCNConv
from spektral.data import Dataset, Graph

# Configurable path: use env var or default relative to repo root
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.environ.get("CODENET_DATASET_PATH", os.path.join(_REPO_ROOT, "Project_CodeNet"))

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}. Set CODENET_DATASET_PATH to point to Project_CodeNet.")

print("Num GPUs Available:", len(tf.config.list_physical_devices('GPU')))
print(f"Using dataset from: {DATASET_PATH}")

# ✅ Tokenizer: Convert source code into token sequences
def tokenize_code(file_content):
    tokens = re.findall(r'\b\w+\b', file_content)
    return tokens[:100]  # Limit sequence length

# ✅ Graph Builder: Convert token sequences into a graph representation
def build_graph(tokens):
    num_nodes = len(tokens)
    x = np.arange(num_nodes).reshape(-1, 1).astype(np.float32)  # Node features
    adj = np.eye(num_nodes)  # Identity matrix as adjacency matrix (placeholder)
    return Graph(x=x, a=adj)

# ✅ Load dataset
def load_project_codenet_data(max_files=1000):
    dataset = []
    labels = []
    file_count = 0  # Counter for limiting files

    for root, _, files in os.walk(DATASET_PATH):
        for file in files:
            if file_count >= max_files:  # Stop after processing `max_files`
                break
            
            if file.endswith((".c", ".cpp", ".py", ".java")):  # Process only relevant files
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                    
                    tokens = tokenize_code(code)
                    graph = build_graph(tokens)

                    dataset.append(graph)
                    labels.append(np.random.randint(0, 3))  # Placeholder labels

                    file_count += 1  # Increment file counter
                except Exception as e:
                    print(f"⚠️ Skipping {file_path}: {e}")

    return dataset, np.array(labels)

# ✅ Load dataset
def data_generator():
    for graph, label in zip(*load_project_codenet_data(max_files=1000)):  # Load only 1000 at a time
        yield (graph.x, graph.a), label

# Convert generator to TensorFlow dataset
dataset = tf.data.Dataset.from_generator(
    data_generator,
    output_signature=(
        (tf.TensorSpec(shape=(None, 1), dtype=tf.float32), tf.TensorSpec(shape=(None, None), dtype=tf.float32)),
        tf.TensorSpec(shape=(), dtype=tf.int32),
    )
).batch(32)  # Process in batches of 32

print(f"✅ Loaded {len(dataset)} training samples from Project_CodeNet")

# ✅ TensorFlow Graph Neural Network (GNN) Model
class ComplexityGNN(tf.keras.Model):
    def __init__(self, hidden_units=64, num_classes=3):
        super().__init__()
        self.conv1 = GCNConv(hidden_units, activation="relu")
        self.conv2 = GCNConv(num_classes, activation="softmax")

    def call(self, inputs):
        x, a = inputs
        x = self.conv1([x, a])
        x = self.conv2([x, a])
        return x

# ✅ Prepare Training Data
X = np.array([g.x for g in dataset])
A = np.array([g.a for g in dataset])
y = tf.keras.utils.to_categorical(labels, num_classes=3)  # One-hot encoding

# ✅ Compile Model
model = ComplexityGNN()
model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])

# ✅ Train Model on GPU
print("🚀 Training on GPU..." if len(tf.config.list_physical_devices('GPU')) > 0 else "🚀 Training on CPU...")
model.fit([X, A], y, epochs=10, batch_size=32)

# ✅ Save Model
model.save("complexity_gnn_tf.h5")
print("✅ Model saved to complexity_gnn_tf.h5")
