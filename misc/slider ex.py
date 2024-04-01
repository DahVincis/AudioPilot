import tkinter as tk
from tkinter import ttk

# Create the Tkinter application window
root = tk.Tk()
root.title("Slider Example")

# Function to update the label text when the slider moves
def update_label(value):
    # Convert the value to a float before performing calculations
    value = float(value)
    label.config(text=f"Selected value: {value/100:.2f}")

# Create a slider widget
slider = ttk.Scale(root, from_=0, to=100, orient="vertical", command=update_label)
slider.pack(padx=10, pady=10)

# Create a label to display the selected value
label = tk.Label(root, text="Selected value: 0.00")
label.pack(padx=10, pady=(0, 10))

# Start the Tkinter event loop
root.mainloop()
