# Card Imposer

A lightweight, automated prepress tool designed to arrange multiple card layouts onto single larger sheets for efficient printing. This utility automates the **step-and-repeat (N-up)** process while managing precise alignments, margins, and cutting marks.

## 🚀 Features

* **Grid Layout Creator (N-Up / Step-and-Repeat):** Easily duplicate a single card design in a grid pattern (e.g., 8-up, 10-up, 24-up) to maximize paper efficiency.
* **Front & Back Duplex Alignment:** Accurately couples double-sided card files so that the front and back line up perfectly when flipped or printed duplex.
* **Bleed & Gutter Management:** Automatically handles bleed zones, safety margins, and custom spacing (gutters) between cards.
* **Smart Trim Marks:** Automatically inserts crop marks, trim lines, and cutting guide marks for guillotine operations or digital card cutters.
* **Multi-Format Sheet Support:** Built-in templates for common press and printer sheets (A4, Letter, SRA3, 12x18 inches, etc.) alongside custom dimension options.

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com

# Navigate to the project directory
cd card-imposer

# Install dependencies (Update based on your project requirements)
npm install # or pip install -r requirements.txt
```

## 💻 Usage

```bash
# Run the application (Update this example to match your execution command)
python main.py --input card.pdf --sheet SRA3 --output imposed_sheet.pdf
```

## ⚙️ Configuration

You can customize the layout via options or a configuration file:
* **Card Dimensions:** Set standard sizes (e.g., Business Cards 3.5" x 2") or custom widths and heights.
* **Sheet Size:** Define target print sheet dimensions.
* **Gutter Size:** Adjust spacing between cards for safe cuts.
* **Bleed Margin:** Set color extension limits (e.g., 0.125" / 3mm).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com).

## 📜 License

This project is licensed under the [MIT License](LICENSE).
