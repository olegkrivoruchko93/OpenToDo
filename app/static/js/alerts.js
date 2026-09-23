// Closing button for messages
var close = document.getElementsByClassName("closebtn");
var i;

for (i = 0; i < close.length; i++) {
  close[i].onclick = function () {
    var div = this.parentElement;
    div.style.opacity = "0";
    setTimeout(function () {
      div.style.display = "none";
    }, 600);
  };
}
const overlay = document.getElementById("overlay");
const elTitle = document.getElementById("task-title");
const elDesc = document.getElementById("task-desc");
const elStatus = document.getElementById("task-status");
const saveBtn = document.getElementById("save-btn");
let currentTaskId = null;

// Open overlay when a task item is clicked
document.querySelectorAll(".task-item").forEach((el) => {
  el.addEventListener("click", async () => {
    const id = el.dataset.taskId;
    currentTaskId = id;
    openOverlay();
    try {
      const res = await fetch(`/tasks/${id}`);
      if (!res.ok) throw new Error("Task not found");
      const task = await res.json();
      elTitle.value = task.title;
      elDesc.value = task.description || "";
      elStatus.value = task.status;
    } catch (err) {
      elTitle.value = "Error";
      elDesc.value = err.message;
      elStatus.value = "todo";
    }
  });
});

// Save task changes
saveBtn.addEventListener("click", async () => {
  if (!currentTaskId) return;
  try {
    const res = await fetch(`/tasks/${currentTaskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: elTitle.value,
        description: elDesc.value,
        status: elStatus.value,
      }),
    });
    if (!res.ok) throw new Error("Failed to save");
    closeOverlay();
  } catch (err) {
    elTitle.value = "Error saving!";
    elDesc.value = err.message;
  }
});

function openOverlay() {
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
}

function closeOverlay() {
  overlay.classList.add("hidden");
  overlay.setAttribute("aria-hidden", "true");
}

// Close on backdrop or close button
overlay.querySelectorAll("[data-close]").forEach((el) => {
  el.addEventListener("click", closeOverlay);
});

// Close on Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeOverlay();
});
