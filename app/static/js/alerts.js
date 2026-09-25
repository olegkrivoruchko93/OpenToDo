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
const elDueDate = document.getElementById("task-due-date");
const elProject = document.getElementById("task-project");
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
      elDueDate.value = task.due_date || "";
      elProject.value = task.project_id || "";
    } catch (err) {
      elTitle.value = "Error";
      elDesc.value = err.message;
      elStatus.value = "todo";
      elDueDate.value = "";
      elProject.value = "";
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
        due_date: elDueDate.value,
        project_id: elProject.value,
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

// Make project items editable on double-click
document.querySelectorAll(".project-item").forEach((el) => {
  el.addEventListener("dblclick", () => {
    const p = el.querySelector("p");
    const projectId = el.dataset.projectId;
    const currentTitle = p.textContent.trim();

    const input = document.createElement("input");
    input.type = "text";
    input.value = currentTitle;
    input.className = "project-edit-input";

    p.replaceWith(input);
    input.focus();
    input.select();

    function save() {
      const newTitle = input.value.trim();
      if (!newTitle || newTitle === currentTitle) {
        input.replaceWith(p);
        return;
      }
      fetch(`/projects/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      })
        .then((res) => {
          if (!res.ok) throw new Error("Failed to save");
          return res.json();
        })
        .then((data) => {
          p.textContent = data.title;
          input.replaceWith(p);
        })
        .catch(() => {
          input.replaceWith(p);
        });
    }

    input.addEventListener("blur", save);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        save();
      } else if (e.key === "Escape") {
        input.replaceWith(p);
      }
    });
  });
});
