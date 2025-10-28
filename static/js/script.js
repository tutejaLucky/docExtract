document.getElementById("uploadBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("pdfFile");
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  const output = document.getElementById("output");

  if (!fileInput.files.length) {
    status.innerText = "⚠️ Please select a PDF file first.";
    return;
  }

  status.innerText = "⏳ Uploading and processing...";
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const response = await fetch("/upload", { 
    method: "POST",
    body: formData,
  });

  const data = await response.json();

  if (data.error) {
    status.innerText = "❌ Error: " + data.error;
  } else {
    status.innerText = "✅ Extraction complete!";
    results.classList.remove("hidden");
    output.textContent = JSON.stringify(data, null, 2);
  }
});
