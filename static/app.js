const {
    csrfToken: CSRF_TOKEN,
    flashMessages: FLASH_MESSAGES,
    searchQuery: CURRENT_SEARCH_QUERY,
    indexUrl: INDEX_URL,
    currentView: CURRENT_VIEW,
    currentProjectId: CURRENT_PROJECT_ID,
    currentTagId: CURRENT_TAG_ID,
    tagSuggestionNames: availableTagNames,
    tagSuggestionItems: availableTagItems,
} = window.APP_CONFIG;

const SIDEBAR_WIDTH_STORAGE_KEY = "openTodoSidebarWidthPx";
const SIDEBAR_WIDTH_MIN = 200;
const SIDEBAR_WIDTH_MAX = 520;
const SIDEBAR_WIDTH_DEFAULT = 290;

function clampSidebarWidthPx(px) {
    const cap = Math.min(SIDEBAR_WIDTH_MAX, Math.floor(window.innerWidth * 0.5));
    return Math.min(cap, Math.max(SIDEBAR_WIDTH_MIN, Math.round(px)));
}

function applySidebarWidthPx(px, persist) {
    const clamped = clampSidebarWidthPx(px);
    document.documentElement.style.setProperty("--sidebar-width", `${clamped}px`);
    if (persist) {
        localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(clamped));
    }
    return clamped;
}

(function initSidebarWidth() {
    const raw = localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY);
    let px = SIDEBAR_WIDTH_DEFAULT;
    if (raw !== null) {
        const parsed = parseInt(raw, 10);
        if (!Number.isNaN(parsed)) {
            px = parsed;
        }
    }
    applySidebarWidthPx(px, false);
})();

window.addEventListener("resize", () => {
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--sidebar-width").trim();
    const current = parseInt(raw, 10);
    if (Number.isNaN(current)) {
        return;
    }
    const clamped = clampSidebarWidthPx(current);
    document.documentElement.style.setProperty("--sidebar-width", `${clamped}px`);
    if (clamped !== current) {
        localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(clamped));
    }
});

const modalOverlay = document.getElementById("task-modal-overlay");
const openTaskModalBtn = document.getElementById("open-task-modal");
const closeTaskModalBtn = document.getElementById("close-task-modal");
const taskTitleInput = document.getElementById("task-title-input");
const projectModalOverlay = document.getElementById("project-modal-overlay");
const openProjectModalBtn = document.getElementById("open-project-modal");
const closeProjectModalBtn = document.getElementById("close-project-modal");
const projectNameInput = document.getElementById("project-name-input");
const editProjectButtons = document.querySelectorAll(".project-action-btn[data-project-id]");
const backupModalOverlay = document.getElementById("backup-modal-overlay");
const closeBackupModalBtn = document.getElementById("close-backup-modal");
const settingsModalOverlay = document.getElementById("settings-modal-overlay");
const openSettingsModalBtn = document.getElementById("open-settings-modal");
const closeSettingsModalBtn = document.getElementById("close-settings-modal");
const settingsOpenBackupBtn = document.getElementById("settings-open-backup-btn");
const projectEditModalOverlay = document.getElementById("project-edit-modal-overlay");
const closeProjectEditModalBtn = document.getElementById("close-project-edit-modal");
const projectEditForm = document.getElementById("project-edit-form");
const projectDeleteForm = document.getElementById("project-delete-form");
const projectEditNameInput = document.getElementById("project-edit-name-input");
const projectEditIconInput = document.getElementById("project-edit-icon-input");
const tagModalOverlay = document.getElementById("tag-modal-overlay");
const openTagModalBtn = document.getElementById("open-tag-modal");
const closeTagModalBtn = document.getElementById("close-tag-modal");
const tagNameInput = document.getElementById("tag-name-input");
const tagColorInput = document.getElementById("tag-color-input");
const editTagButtons = document.querySelectorAll(".project-action-btn[data-tag-id]");
const tagEditModalOverlay = document.getElementById("tag-edit-modal-overlay");
const closeTagEditModalBtn = document.getElementById("close-tag-edit-modal");
const tagEditForm = document.getElementById("tag-edit-form");
const tagDeleteForm = document.getElementById("tag-delete-form");
const tagEditNameInput = document.getElementById("tag-edit-name-input");
const tagEditColorInput = document.getElementById("tag-edit-color-input");
const taskChecklistItems = document.getElementById("task-checklist-items");
const taskAddChecklistItemBtn = document.getElementById("task-add-checklist-item");
const taskDueDateInput = document.getElementById("task-due-date-input");
const taskRecurrenceInput = document.getElementById("task-recurrence-input");
const taskPriorityInput = document.getElementById("task-priority-input");
const taskTagsInput = document.getElementById("task-tags-input");
const taskTagsSuggestions = document.getElementById("task-tags-suggestions");
const taskEditModalOverlay = document.getElementById("task-edit-modal-overlay");
const closeTaskEditModalBtn = document.getElementById("close-task-edit-modal");
const taskEditForm = document.getElementById("task-edit-form");
const taskEditDeleteForm = document.getElementById("task-edit-delete-form");
const taskEditTitleInput = document.getElementById("task-edit-title-input");
const taskEditDescriptionInput = document.getElementById("task-edit-description-input");
const taskEditDueDateInput = document.getElementById("task-edit-due-date-input");
const taskEditRecurrenceInput = document.getElementById("task-edit-recurrence-input");
const taskEditPriorityInput = document.getElementById("task-edit-priority-input");
const taskEditProjectInput = document.getElementById("task-edit-project-input");
const taskEditTagsInput = document.getElementById("task-edit-tags-input");
const taskEditTagsSuggestions = document.getElementById("task-edit-tags-suggestions");
const taskEditTagsPicker = document.getElementById("task-edit-tags-picker");
const taskEditTagsSelected = document.getElementById("task-edit-tags-selected");
const taskEditTagsSearch = document.getElementById("task-edit-tags-search");
const taskEditChecklistProgress = document.getElementById("task-edit-checklist-progress");
const taskEditChecklistItems = document.getElementById("task-edit-checklist-items");
const taskEditAddChecklistItemBtn = document.getElementById("task-edit-add-checklist-item");
const taskEditAttachments = document.getElementById("task-edit-attachments");
const taskEditNewAttachmentsInput = document.getElementById("task-edit-new-attachments-input");
const taskItems = document.querySelectorAll(".task-item[data-task-id]");
const taskListEl = document.querySelector(".task-list");
const taskEditSaveBtn = document.getElementById("task-edit-save-btn");
const toastEl = document.getElementById("toast");
let editingTaskId = null;
const removeCompletedTaskTimeouts = new Map();
let toastTimeoutId;

const THEME_STORAGE_KEY = "opentodo-theme";
const THEME_VALUES = ["default", "warm", "dark", "ocean", "forest", "violet", "autumn", "sky", "gravel"];
const TASK_PRIORITY_VALUES = ["high", "medium", "low"];
const themeOptionButtons = document.querySelectorAll(".theme-option[data-theme-value]");

function getStoredTheme() {
    const v = localStorage.getItem(THEME_STORAGE_KEY);
    if (THEME_VALUES.includes(v)) {
        return v;
    }
    return "default";
}

function applyTheme(theme) {
    const t = THEME_VALUES.includes(theme) ? theme : "default";
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem(THEME_STORAGE_KEY, t);
    themeOptionButtons.forEach((btn) => {
        const on = btn.getAttribute("data-theme-value") === t;
        btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
}

applyTheme(getStoredTheme());

themeOptionButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        applyTheme(btn.getAttribute("data-theme-value"));
    });
});

function removeTaskJsonScript(taskId) {
    document.getElementById(`task-json-${taskId}`)?.remove();
}

function syncModalOpenState() {
    const hasOpenModal = Boolean(document.querySelector(".modal-overlay:not(.hidden)"));
    document.body.classList.toggle("modal-open", hasOpenModal);
}

function showToast(message) {
    if (!toastEl) {
        return;
    }
    clearTimeout(toastTimeoutId);
    toastEl.textContent = message;
    toastEl.classList.remove("hidden");
    toastTimeoutId = window.setTimeout(() => {
        toastEl.classList.add("hidden");
    }, 5000);
}

function normalizeTaskPriority(value) {
    return TASK_PRIORITY_VALUES.includes(value) ? value : "medium";
}

function buildTaskFilterUrl({ projectId = CURRENT_PROJECT_ID, tagId = CURRENT_TAG_ID } = {}) {
    const params = new URLSearchParams();
    params.set("view", CURRENT_VIEW);
    if (projectId) {
        params.set("project_id", projectId);
    }
    if (tagId) {
        params.set("tag_id", tagId);
    }
    if (CURRENT_SEARCH_QUERY) {
        params.set("q", CURRENT_SEARCH_QUERY);
    }
    const query = params.toString();
    return query ? `${INDEX_URL}?${query}` : INDEX_URL;
}

function syncPriorityPicker(input) {
    if (!input) {
        return;
    }
    const priority = normalizeTaskPriority(input.value);
    input.value = priority;
    const selected = document.querySelector(`[data-priority-selected-for="${input.id}"]`);
    const selectedButton = document.querySelector(`[data-priority-target="${input.id}"][data-priority-option="${priority}"]`);
    document.querySelectorAll(`[data-priority-target="${input.id}"]`).forEach((button) => {
        const isActive = button.dataset.priorityOption === priority;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
    if (selected && selectedButton) {
        selected.className = `priority-selected priority-option-${priority}`;
        selected.innerHTML = selectedButton.innerHTML;
    }
}

document.querySelectorAll("[data-priority-option][data-priority-target]").forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.priorityTarget);
        if (!input) {
            return;
        }
        input.value = normalizeTaskPriority(button.dataset.priorityOption);
        syncPriorityPicker(input);
        document.querySelector(`[data-priority-dropdown="${input.id}"]`)?.removeAttribute("open");
    });
});
document.addEventListener("click", (event) => {
    document.querySelectorAll(".priority-dropdown[open]").forEach((dropdown) => {
        if (!dropdown.contains(event.target)) {
            dropdown.removeAttribute("open");
        }
    });
});
syncPriorityPicker(taskPriorityInput);
syncPriorityPicker(taskEditPriorityInput);

if (FLASH_MESSAGES.length) {
    showToast(FLASH_MESSAGES.join(" • "));
}

function isMobileViewport() {
    return window.matchMedia("(max-width: 768px)").matches;
}

document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.confirm) {
        return;
    }
    if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
    }
});

function ensureTaskListEmptyState() {
    if (!taskListEl) {
        return;
    }
    if (taskListEl.querySelector(".task-item[data-task-id]") || taskListEl.querySelector(".empty-state")) {
        return;
    }
    const li = document.createElement("li");
    li.className = "empty-state";
    const currentView = document.body.dataset.currentView;
    if (currentView === "trash") {
        li.innerHTML = "<h3>В корзине пусто</h3><p>Удаленные задачи появляются здесь перед окончательным удалением.</p>";
    } else if (currentView === "archive") {
        li.innerHTML = "<h3>В архиве пусто</h3><p>Выполненные задачи появляются здесь после отметки «готово».</p>";
    } else {
        li.innerHTML = "<h3>Тут пока ничего нет</h3><p>Нажмите на кнопку \"Новая задача\" и начните планирование.</p>";
    }
    taskListEl.appendChild(li);
}

if (taskListEl) {
    taskListEl.addEventListener("submit", async (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) {
            return;
        }
        if (!form.matches("[data-task-toggle-form]")) {
            return;
        }
        const taskItem = form.closest(".task-item[data-task-id]");
        if (!taskItem) {
            return;
        }
        event.preventDefault();
        const taskId = taskItem.dataset.taskId;
        const existingTimeout = removeCompletedTaskTimeouts.get(taskId);
        if (existingTimeout !== undefined) {
            clearTimeout(existingTimeout);
            removeCompletedTaskTimeouts.delete(taskId);
        }
        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": CSRF_TOKEN,
                },
            });
            let payload;
            try {
                payload = await response.json();
            } catch (parseErr) {
                alert("Не удалось обновить задачу.");
                return;
            }
            if (!response.ok || !payload.ok) {
                alert(payload.error || "Не удалось обновить задачу.");
                return;
            }
            const toggleBtn = form.querySelector("button.icon-btn");
            const isTrashView = document.body.dataset.currentView === "trash";
            const isArchiveView = document.body.dataset.currentView === "archive";
            if (payload.is_done) {
                taskItem.classList.add("done");
                if (toggleBtn) {
                    toggleBtn.textContent = "✓";
                }
                if (!isTrashView && !isArchiveView) {
                    const timeoutId = setTimeout(() => {
                        removeCompletedTaskTimeouts.delete(taskId);
                        taskItem.remove();
                        removeTaskJsonScript(taskId);
                        ensureTaskListEmptyState();
                    }, 5000);
                    removeCompletedTaskTimeouts.set(taskId, timeoutId);
                }
            } else {
                taskItem.classList.remove("done");
                if (toggleBtn) {
                    toggleBtn.textContent = "";
                }
                if (isTrashView || isArchiveView) {
                    taskItem.remove();
                    removeTaskJsonScript(taskId);
                    ensureTaskListEmptyState();
                }
            }
        } catch (err) {
            alert("Ошибка сети при обновлении задачи.");
        }
    });
}

const sidebarResizer = document.getElementById("sidebar-resizer");
if (sidebarResizer) {
    sidebarResizer.addEventListener("mousedown", (downEvent) => {
        downEvent.preventDefault();
        const onMove = (e) => applySidebarWidthPx(e.clientX, false);
        const onUp = () => {
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
            const current = parseInt(
                getComputedStyle(document.documentElement).getPropertyValue("--sidebar-width").trim(),
                10
            );
            if (!Number.isNaN(current)) {
                applySidebarWidthPx(current, true);
            }
        };
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    });
    sidebarResizer.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") {
            return;
        }
        e.preventDefault();
        const current = parseInt(
            getComputedStyle(document.documentElement).getPropertyValue("--sidebar-width").trim(),
            10
        );
        if (Number.isNaN(current)) {
            return;
        }
        const delta = e.key === "ArrowRight" ? 8 : -8;
        applySidebarWidthPx(current + delta, true);
    });
}

function openTaskModal() {
    if (taskChecklistItems.childElementCount === 0) {
        addChecklistInput();
    }
    modalOverlay.classList.remove("hidden");
    syncModalOpenState();
    taskTitleInput.focus();
}

function closeTaskModal() {
    modalOverlay.classList.add("hidden");
    syncModalOpenState();
}

function addChecklistInput(initialValue = "") {
    const row = document.createElement("div");
    row.className = "checklist-builder-row";
    const input = document.createElement("input");
    input.type = "text";
    input.name = "checklist_items[]";
    input.placeholder = "Пункт чеклиста";
    input.value = initialValue;
    input.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") {
            return;
        }
        event.preventDefault();
        if (!input.value.trim()) {
            return;
        }
        addChecklistInput().focus();
    });
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "icon-btn remove-checklist-item-btn";
    removeBtn.textContent = "✕";
    row.append(input, removeBtn);
    taskChecklistItems.appendChild(row);
    removeBtn.addEventListener("click", () => {
        row.remove();
        if (taskChecklistItems.childElementCount === 0) {
            addChecklistInput().focus();
        }
    });
    return input;
}

function updateEditChecklistProgress() {
    if (!taskEditChecklistProgress) {
        return;
    }
    const rows = Array.from(taskEditChecklistItems.querySelectorAll(".checklist-builder-row"));
    const filledRows = rows.filter((row) => {
        const titleInput = row.querySelector('input[name="checklist_items[]"]');
        return titleInput && titleInput.value.trim();
    });
    if (filledRows.length === 0) {
        taskEditChecklistProgress.textContent = "";
        return;
    }
    const doneCount = filledRows.filter((row) => {
        const checkbox = row.querySelector(".checklist-done-toggle");
        return checkbox && checkbox.checked;
    }).length;
    const progress = Math.round((doneCount / filledRows.length) * 100);
    taskEditChecklistProgress.textContent = `(выполнено на ${progress}%)`;
}

function addEditChecklistInput(itemId = "", itemTitle = "", isDone = false) {
    const row = document.createElement("div");
    row.className = "checklist-builder-row";
    const idInput = document.createElement("input");
    idInput.type = "hidden";
    idInput.name = "checklist_item_id[]";
    idInput.value = itemId;
    const doneInput = document.createElement("input");
    doneInput.type = "hidden";
    doneInput.name = "checklist_item_done[]";
    doneInput.value = isDone ? "1" : "0";
    const doneCheckbox = document.createElement("input");
    doneCheckbox.type = "checkbox";
    doneCheckbox.className = "checklist-done-toggle";
    doneCheckbox.checked = isDone;
    doneCheckbox.setAttribute("aria-label", "Отметить пункт чеклиста выполненным");
    row.classList.toggle("done", isDone);
    doneCheckbox.addEventListener("change", () => {
        doneInput.value = doneCheckbox.checked ? "1" : "0";
        row.classList.toggle("done", doneCheckbox.checked);
        updateEditChecklistProgress();
    });
    const titleInput = document.createElement("input");
    titleInput.type = "text";
    titleInput.name = "checklist_items[]";
    titleInput.placeholder = "Пункт чеклиста";
    titleInput.value = itemTitle;
    titleInput.addEventListener("input", updateEditChecklistProgress);
    titleInput.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") {
            return;
        }
        event.preventDefault();
        if (!titleInput.value.trim()) {
            return;
        }
        addEditChecklistInput("", "", false).focus();
    });
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "icon-btn remove-checklist-item-btn";
    removeBtn.textContent = "✕";
    row.append(idInput, doneInput, doneCheckbox, titleInput, removeBtn);
    taskEditChecklistItems.appendChild(row);
    removeBtn.addEventListener("click", () => {
        row.remove();
        if (taskEditChecklistItems.childElementCount === 0) {
            addEditChecklistInput("", "", false).focus();
        }
        updateEditChecklistProgress();
    });
    updateEditChecklistProgress();
    return titleInput;
}

function attachFileDropzones() {
    document.querySelectorAll(".file-dropzone").forEach((dropzone) => {
        const input = dropzone.querySelector('input[type="file"]');
        const title = dropzone.querySelector(".file-dropzone-title");
        if (!input || !title) {
            return;
        }

        const updateTitle = () => {
            const fileCount = input.files ? input.files.length : 0;
            title.textContent = fileCount > 0
                ? `Выбрано файлов: ${fileCount}`
                : "Прикрепить файлы";
        };

        input.addEventListener("change", updateTitle);

        dropzone.addEventListener("dragover", (event) => {
            event.preventDefault();
            dropzone.classList.add("drag-over");
        });

        dropzone.addEventListener("dragleave", () => {
            dropzone.classList.remove("drag-over");
        });

        dropzone.addEventListener("drop", (event) => {
            event.preventDefault();
            dropzone.classList.remove("drag-over");
            if (!event.dataTransfer?.files.length) {
                return;
            }
            input.files = event.dataTransfer.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
        });
    });
}

function resizeTaskEditDescriptionInput() {
    if (!taskEditDescriptionInput) {
        return;
    }
    if (!taskEditDescriptionInput.dataset.singleLineHeight) {
        taskEditDescriptionInput.style.height = "";
        taskEditDescriptionInput.dataset.singleLineHeight = String(taskEditDescriptionInput.offsetHeight || 36);
    }

    const singleLineHeight = Number(taskEditDescriptionInput.dataset.singleLineHeight);
    taskEditDescriptionInput.style.height = `${singleLineHeight}px`;
    if (taskEditDescriptionInput.scrollHeight > taskEditDescriptionInput.clientHeight) {
        taskEditDescriptionInput.style.height = `${taskEditDescriptionInput.scrollHeight}px`;
    }
}

function parseTagInputState(input) {
    const raw = input.value || "";
    const parts = raw.split(",");
    const currentRaw = parts.pop() || "";
    const prefix = parts.length > 0 ? `${parts.join(",").trim()}, ` : "";
    const selected = parts
        .map((part) => part.trim().toLowerCase())
        .filter(Boolean);
    return {
        current: currentRaw.trim(),
        prefix,
        selected,
    };
}

function applyTagSuggestion(input, suggestionsEl, tagName) {
    const state = parseTagInputState(input);
    input.value = `${state.prefix}${tagName}, `;
    suggestionsEl.classList.add("hidden");
    input.focus();
}

function renderTagSuggestions(input, suggestionsEl) {
    const state = parseTagInputState(input);
    const query = state.current.toLowerCase();
    suggestionsEl.innerHTML = "";

    if (!state.current) {
        suggestionsEl.classList.add("hidden");
        return;
    }

    const matches = availableTagNames
        .filter((tagName) => !state.selected.includes(tagName.toLowerCase()))
        .filter((tagName) => tagName.toLowerCase().includes(query))
        .slice(0, 8);
    const hasExactMatch = availableTagNames.some((tagName) => tagName.toLowerCase() === query);

    matches.forEach((tagName) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tag-suggestion-item";
        button.textContent = tagName;
        button.addEventListener("mousedown", (event) => {
            event.preventDefault();
            applyTagSuggestion(input, suggestionsEl, tagName);
        });
        suggestionsEl.appendChild(button);
    });

    if (!hasExactMatch) {
        const addButton = document.createElement("button");
        addButton.type = "button";
        addButton.className = "tag-suggestion-item tag-suggestion-add";
        addButton.textContent = `Добавить «${state.current}»`;
        addButton.addEventListener("mousedown", (event) => {
            event.preventDefault();
            applyTagSuggestion(input, suggestionsEl, state.current);
        });
        suggestionsEl.appendChild(addButton);
    }

    suggestionsEl.classList.toggle("hidden", suggestionsEl.childElementCount === 0);
}

function attachTagAutocomplete(input, suggestionsEl) {
    input.addEventListener("input", () => renderTagSuggestions(input, suggestionsEl));
    input.addEventListener("focus", () => renderTagSuggestions(input, suggestionsEl));
    input.addEventListener("blur", () => {
        setTimeout(() => suggestionsEl.classList.add("hidden"), 120);
    });
    input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            suggestionsEl.classList.add("hidden");
        }
    });
}

const knownTagColorsByLower = new Map(
    availableTagItems.map((tag) => [String(tag.name || "").toLowerCase(), normalizeTagColorForInput(tag.color)])
);

function hexToRgba(hex, alpha) {
    const normalized = normalizeTagColorForInput(hex).replace("#", "");
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function splitTagNames(raw) {
    const seen = new Set();
    return String(raw || "")
        .split(",")
        .map((part) => part.trim())
        .filter((name) => {
            if (!name) {
                return false;
            }
            const key = name.toLowerCase();
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
}

function getTaskEditSelectedTagNames() {
    return splitTagNames(taskEditTagsInput.value);
}

function setTaskEditSelectedTagNames(names) {
    taskEditTagsInput.value = splitTagNames(names.join(", ")).join(", ");
    renderTaskEditTagPicker();
    renderTaskEditTagMenu();
}

function rememberTaskTags(tags = []) {
    tags.forEach((tag) => {
        const name = String(tag.name || "").trim();
        if (!name) {
            return;
        }
        const key = name.toLowerCase();
        const color = normalizeTagColorForInput(tag.color);
        knownTagColorsByLower.set(key, color);
        if (!availableTagItems.some((item) => String(item.name || "").toLowerCase() === key)) {
            availableTagItems.push({ name, color });
            availableTagNames.push(name);
        }
    });
}

function getKnownTagColor(name) {
    return knownTagColorsByLower.get(String(name || "").toLowerCase()) || "#5b7cfa";
}

function renderTaskEditTagPicker() {
    const selectedNames = getTaskEditSelectedTagNames();
    taskEditTagsSelected.innerHTML = "";
    selectedNames.forEach((name) => {
        const color = getKnownTagColor(name);
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "tag-picker-chip";
        chip.style.background = hexToRgba(color, 0.18);
        chip.style.borderColor = hexToRgba(color, 0.32);
        chip.style.color = color;
        chip.setAttribute("aria-label", `Убрать метку ${name}`);

        const label = document.createElement("span");
        label.textContent = name;
        const remove = document.createElement("span");
        remove.className = "tag-picker-chip-remove";
        remove.setAttribute("aria-hidden", "true");
        remove.textContent = "✕";
        chip.append(label, remove);
        chip.addEventListener("click", (event) => {
            event.stopPropagation();
            setTaskEditSelectedTagNames(selectedNames.filter((selectedName) => selectedName.toLowerCase() !== name.toLowerCase()));
            taskEditTagsSearch.focus();
        });
        taskEditTagsSelected.appendChild(chip);
    });
    taskEditTagsSearch.placeholder = selectedNames.length ? "" : "Добавить метку";
}

function openTaskEditTagMenu() {
    taskEditTagsSuggestions.classList.remove("hidden");
    taskEditTagsPicker.setAttribute("aria-expanded", "true");
    renderTaskEditTagMenu();
}

function closeTaskEditTagMenu() {
    taskEditTagsSuggestions.classList.add("hidden");
    taskEditTagsPicker.setAttribute("aria-expanded", "false");
}

function toggleTaskEditTag(name) {
    const selectedNames = getTaskEditSelectedTagNames();
    const key = String(name || "").trim().toLowerCase();
    if (!key) {
        return;
    }
    const exists = selectedNames.some((selectedName) => selectedName.toLowerCase() === key);
    setTaskEditSelectedTagNames(
        exists
            ? selectedNames.filter((selectedName) => selectedName.toLowerCase() !== key)
            : selectedNames.concat(String(name || "").trim())
    );
}

function addTaskEditTagFromSearch() {
    const typedName = taskEditTagsSearch.value.trim();
    if (!typedName) {
        return false;
    }
    const existing = availableTagItems.find((tag) => String(tag.name || "").toLowerCase() === typedName.toLowerCase());
    const tagName = existing ? existing.name : typedName;
    const selectedNames = getTaskEditSelectedTagNames();
    if (!selectedNames.some((selectedName) => selectedName.toLowerCase() === String(tagName).toLowerCase())) {
        setTaskEditSelectedTagNames(selectedNames.concat(tagName));
    }
    taskEditTagsSearch.value = "";
    openTaskEditTagMenu();
    return true;
}

function renderTaskEditTagMenu() {
    const selectedNames = getTaskEditSelectedTagNames();
    const selectedKeys = selectedNames.map((name) => name.toLowerCase());
    const query = taskEditTagsSearch.value.trim().toLowerCase();
    taskEditTagsSuggestions.innerHTML = "";

    const matches = availableTagItems
        .filter((tag) => String(tag.name || "").toLowerCase().includes(query))
        .slice(0, 10);

    matches.forEach((tag) => {
        const name = String(tag.name || "").trim();
        if (!name) {
            return;
        }
        const color = normalizeTagColorForInput(tag.color);
        const selected = selectedKeys.includes(name.toLowerCase());
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tag-picker-option";
        button.classList.toggle("selected", selected);
        button.setAttribute("role", "option");
        button.setAttribute("aria-selected", selected ? "true" : "false");
        button.addEventListener("mousedown", (event) => {
            event.preventDefault();
            taskEditTagsSearch.value = "";
            toggleTaskEditTag(name);
            taskEditTagsSearch.focus();
        });

        const icon = document.createElement("span");
        icon.className = "tag-picker-option-icon";
        icon.style.color = color;
        icon.textContent = "🏷";
        const label = document.createElement("span");
        label.className = "tag-picker-option-label";
        label.textContent = name;
        const check = document.createElement("span");
        check.className = "tag-picker-option-check";
        check.textContent = selected ? "✓" : "";
        button.append(icon, label, check);
        taskEditTagsSuggestions.appendChild(button);
    });

    const hasExactMatch = availableTagItems.some((tag) => String(tag.name || "").toLowerCase() === query);
    if (query && !hasExactMatch) {
        const addButton = document.createElement("button");
        addButton.type = "button";
        addButton.className = "tag-picker-option tag-picker-option-add";
        addButton.addEventListener("mousedown", (event) => {
            event.preventDefault();
            addTaskEditTagFromSearch();
            taskEditTagsSearch.focus();
        });

        const icon = document.createElement("span");
        icon.className = "tag-picker-option-icon";
        icon.textContent = "+";
        const label = document.createElement("span");
        label.className = "tag-picker-option-label";
        label.textContent = `Добавить «${taskEditTagsSearch.value.trim()}»`;
        addButton.append(icon, label);
        taskEditTagsSuggestions.appendChild(addButton);
    }

    taskEditTagsSuggestions.classList.toggle("hidden", taskEditTagsSuggestions.childElementCount === 0);
    taskEditTagsPicker.setAttribute("aria-expanded", taskEditTagsSuggestions.classList.contains("hidden") ? "false" : "true");
}

function attachTaskEditTagPicker() {
    renderTaskEditTagPicker();
    taskEditTagsPicker.addEventListener("click", () => {
        taskEditTagsSearch.focus();
        openTaskEditTagMenu();
    });
    taskEditTagsSearch.addEventListener("focus", openTaskEditTagMenu);
    taskEditTagsSearch.addEventListener("input", renderTaskEditTagMenu);
    taskEditTagsSearch.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            addTaskEditTagFromSearch();
        } else if (event.key === "Backspace" && !taskEditTagsSearch.value) {
            const selectedNames = getTaskEditSelectedTagNames();
            if (selectedNames.length) {
                setTaskEditSelectedTagNames(selectedNames.slice(0, -1));
            }
        } else if (event.key === "Escape") {
            closeTaskEditTagMenu();
        }
    });
    document.addEventListener("mousedown", (event) => {
        if (taskEditTagsPicker.contains(event.target) || taskEditTagsSuggestions.contains(event.target)) {
            return;
        }
        closeTaskEditTagMenu();
    });
}

function renderTaskEditAttachments(attachments = []) {
    taskEditAttachments.innerHTML = "";
    if (!attachments.length) {
        const empty = document.createElement("p");
        empty.className = "attachment-empty";
        empty.textContent = "Вложений пока нет.";
        taskEditAttachments.appendChild(empty);
        return;
    }
    attachments.forEach((attachment) => {
        const row = document.createElement("div");
        row.className = "attachment-row";
        const icon = document.createElement("span");
        icon.className = "attachment-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "📎";
        const meta = document.createElement("div");
        meta.className = "attachment-meta";
        const link = document.createElement("a");
        link.className = "attachment-link";
        link.href = attachment.download_url || "#";
        link.textContent = attachment.filename || "attachment";
        const size = document.createElement("span");
        size.className = "attachment-size";
        size.textContent = attachment.formatted_size || "";
        meta.append(link, size);
        const label = document.createElement("label");
        label.className = "attachment-delete-label";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.name = "delete_attachment_ids[]";
        checkbox.value = String(attachment.id || "");
        checkbox.addEventListener("change", () => {
            if (!checkbox.checked) {
                return;
            }
            const ok = window.confirm("Удалить это вложение после сохранения задачи?");
            if (!ok) {
                checkbox.checked = false;
            }
        });
        label.append(checkbox, "Удалить");
        row.append(icon, meta, label);
        taskEditAttachments.appendChild(row);
    });
}

function openTaskEditModal(taskId) {
    const dataElement = document.getElementById(`task-json-${taskId}`);
    if (!dataElement) {
        return;
    }
    const taskData = JSON.parse(dataElement.textContent);
    editingTaskId = taskId;
    const editParams = new URLSearchParams({
        view: CURRENT_VIEW,
        project_id: CURRENT_PROJECT_ID,
        tag_id: CURRENT_TAG_ID,
    });
    if (CURRENT_SEARCH_QUERY) {
        editParams.set("q", CURRENT_SEARCH_QUERY);
    }
    taskEditForm.action = `/edit/${taskId}?${editParams.toString()}`;
    taskEditDeleteForm.action = `/delete/${taskId}?${editParams.toString()}`;
    taskEditDeleteForm.dataset.confirm = CURRENT_VIEW === "trash"
        ? "Удалить заметку безвозвратно?"
        : "Переместить заметку в корзину?";
    taskEditTitleInput.value = taskData.title || "";
    taskEditDescriptionInput.value = taskData.description || "";
    taskEditDueDateInput.value = taskData.due_at || "";
    taskEditRecurrenceInput.value = taskData.recurrence || "";
    taskEditPriorityInput.value = normalizeTaskPriority(taskData.priority);
    syncPriorityPicker(taskEditPriorityInput);
    taskEditProjectInput.value = taskData.project_id || "";
    taskEditTagsInput.value = taskData.tag_names || "";
    rememberTaskTags(taskData.tags || []);
    taskEditTagsSearch.value = "";
    renderTaskEditTagPicker();
    closeTaskEditTagMenu();
    taskEditChecklistItems.innerHTML = "";
    (taskData.checklist_items || []).forEach((item) => {
        addEditChecklistInput(String(item.id), item.title || "", Boolean(item.is_done));
    });
    if (taskEditChecklistItems.childElementCount === 0) {
        addEditChecklistInput("", "", false);
    }
    updateEditChecklistProgress();
    renderTaskEditAttachments(taskData.attachments || []);
    taskEditNewAttachmentsInput.value = "";
    taskEditNewAttachmentsInput.dispatchEvent(new Event("change", { bubbles: true }));
    taskEditModalOverlay.classList.remove("hidden");
    syncModalOpenState();
    requestAnimationFrame(resizeTaskEditDescriptionInput);
    taskEditTitleInput.focus();
}

function closeTaskEditModal() {
    editingTaskId = null;
    closeTaskEditTagMenu();
    taskEditModalOverlay.classList.add("hidden");
    syncModalOpenState();
}

function updateTaskCard(taskData) {
    const taskItem = document.querySelector(`.task-item[data-task-id="${taskData.id}"]`);
    if (!taskItem) {
        return;
    }
    rememberTaskTags(taskData.tags || []);
    const priority = normalizeTaskPriority(taskData.priority);
    TASK_PRIORITY_VALUES.forEach((value) => {
        taskItem.classList.remove(`task-priority-${value}`);
    });
    taskItem.classList.add(`task-priority-${priority}`);

    const titleEl = taskItem.querySelector(".task-title");
    if (titleEl) {
        titleEl.textContent = taskData.title;
    }

    let indicators = taskItem.querySelector(".task-indicators");
    if (!indicators) {
        const primaryRow = taskItem.querySelector(".task-row-primary");
        if (primaryRow) {
            indicators = document.createElement("div");
            indicators.className = "task-indicators";
            primaryRow.appendChild(indicators);
        }
    }

    const upsertMetaIcon = (key, title, label) => {
        if (!indicators) {
            return;
        }
        let iconEl = indicators.querySelector(`[data-meta-icon="${key}"]`);
        if (label) {
            if (!iconEl) {
                iconEl = document.createElement("span");
                iconEl.className = "task-meta-icon";
                iconEl.dataset.metaIcon = key;
                indicators.appendChild(iconEl);
            }
            iconEl.title = title;
            iconEl.textContent = label;
        } else if (iconEl) {
            iconEl.remove();
        }
    };

    upsertMetaIcon(
        "description",
        "Есть описание",
        (taskData.description || "").trim() ? "📄" : ""
    );
    const checklistCount = Array.isArray(taskData.checklist_items) ? taskData.checklist_items.length : 0;
    upsertMetaIcon(
        "checklist",
        `Чек-лист: ${checklistCount}`,
        checklistCount > 0 ? `☑ ${checklistCount}` : ""
    );
    const attachmentCount = Array.isArray(taskData.attachments) ? taskData.attachments.length : 0;
    upsertMetaIcon(
        "attachment",
        `Вложения: ${attachmentCount}`,
        attachmentCount > 0 ? `📎 ${attachmentCount}` : ""
    );

    let metaRow = taskItem.querySelector(".task-row-meta");
    const hasMeta = Boolean(
        taskData.formatted_due_date
        || taskData.recurrence_label
        || taskData.project_name
        || (taskData.tags && taskData.tags.length > 0)
    );
    if (hasMeta && !metaRow) {
        const taskBody = taskItem.querySelector(".task-body");
        if (taskBody) {
            metaRow = document.createElement("div");
            metaRow.className = "task-row-meta";
            taskBody.appendChild(metaRow);
        }
    } else if (!hasMeta && metaRow) {
        metaRow.remove();
        metaRow = null;
    }

    if (!metaRow) {
        const dataElement = document.getElementById(`task-json-${taskData.id}`);
        if (dataElement) {
            dataElement.textContent = JSON.stringify(taskData);
        }
        return;
    }

    metaRow.querySelectorAll(".date-badge, .recurrence-badge, .project-badge, .task-tag").forEach((el) => {
        el.remove();
    });

    if (taskData.formatted_due_date) {
        const span = document.createElement("span");
        span.className = "date-badge";
        span.textContent = taskData.formatted_due_date;
        metaRow.appendChild(span);
    }

    if (taskData.recurrence_label) {
        const span = document.createElement("span");
        span.className = "recurrence-badge";
        span.textContent = `↻ ${taskData.recurrence_label}`;
        metaRow.appendChild(span);
    }

    if (taskData.project_name) {
        const link = document.createElement("a");
        link.className = "project-badge";
        link.href = buildTaskFilterUrl({ projectId: taskData.project_id });
        link.textContent = `${taskData.project_icon} ${taskData.project_name}`;
        metaRow.appendChild(link);
    }

    if (taskData.tags && taskData.tags.length > 0) {
        taskData.tags.forEach((tag) => {
            const tagEl = document.createElement("a");
            tagEl.className = "task-tag";
            tagEl.href = buildTaskFilterUrl({ tagId: tag.id });
            tagEl.style.background = normalizeTagColorForInput(tag.color);
            tagEl.textContent = tag.name || "";
            metaRow.appendChild(tagEl);
        });
    }

    const oldChecklistBlock = taskItem.querySelector(".checklist-block");
    if (oldChecklistBlock) {
        oldChecklistBlock.remove();
    }

    const dataElement = document.getElementById(`task-json-${taskData.id}`);
    if (dataElement) {
        dataElement.textContent = JSON.stringify(taskData);
    }
}

function openProjectModal() {
    projectModalOverlay.classList.remove("hidden");
    syncModalOpenState();
    projectNameInput.focus();
}

function closeProjectModal() {
    projectModalOverlay.classList.add("hidden");
    syncModalOpenState();
}

function openProjectEditModal(projectId, projectName, projectIcon) {
    const projectParams = new URLSearchParams({
        view: CURRENT_VIEW,
        selected_project_id: CURRENT_PROJECT_ID,
    });
    if (CURRENT_SEARCH_QUERY) {
        projectParams.set("q", CURRENT_SEARCH_QUERY);
    }
    projectEditForm.action = `/projects/edit/${projectId}?${projectParams.toString()}`;
    projectDeleteForm.action = `/projects/delete/${projectId}?${projectParams.toString()}`;
    projectEditNameInput.value = projectName;
    projectEditIconInput.value = projectIcon;
    projectEditModalOverlay.classList.remove("hidden");
    syncModalOpenState();
    projectEditNameInput.focus();
}

function closeProjectEditModal() {
    projectEditModalOverlay.classList.add("hidden");
    syncModalOpenState();
}

function syncColorInputPreview(input) {
    input.style.setProperty("--selected-tag-color", normalizeTagColorForInput(input.value));
}

function openTagModal() {
    syncColorInputPreview(tagColorInput);
    tagModalOverlay.classList.remove("hidden");
    syncModalOpenState();
    tagNameInput.focus();
}

function closeTagModal() {
    tagModalOverlay.classList.add("hidden");
    syncModalOpenState();
}

function normalizeTagColorForInput(raw) {
    const s = (raw || "").trim();
    if (/^#[0-9a-fA-F]{6}$/.test(s)) {
        return s.toLowerCase();
    }
    if (/^#[0-9a-fA-F]{3}$/.test(s)) {
        const r = s[1];
        const g = s[2];
        const b = s[3];
        return `#${r}${r}${g}${g}${b}${b}`.toLowerCase();
    }
    return "#5b7cfa";
}

function openTagEditModal(tagId, tagName, tagColor) {
    tagEditForm.action = `/tags/edit/${tagId}`;
    tagDeleteForm.action = `/tags/delete/${tagId}`;
    tagEditNameInput.value = tagName;
    tagEditColorInput.value = normalizeTagColorForInput(tagColor);
    syncColorInputPreview(tagEditColorInput);
    tagEditModalOverlay.classList.remove("hidden");
    syncModalOpenState();
    tagEditNameInput.focus();
}

function closeTagEditModal() {
    tagEditModalOverlay.classList.add("hidden");
    syncModalOpenState();
}

function openBackupModal() {
    backupModalOverlay.classList.remove("hidden");
    syncModalOpenState();
}

function closeBackupModal() {
    backupModalOverlay.classList.add("hidden");
    syncModalOpenState();
}

function openSettingsModal() {
    applyTheme(getStoredTheme());
    settingsModalOverlay.classList.remove("hidden");
    syncModalOpenState();
}

function closeSettingsModal() {
    settingsModalOverlay.classList.add("hidden");
    syncModalOpenState();
}

syncColorInputPreview(tagColorInput);
syncColorInputPreview(tagEditColorInput);
tagColorInput.addEventListener("input", () => syncColorInputPreview(tagColorInput));
tagEditColorInput.addEventListener("input", () => syncColorInputPreview(tagEditColorInput));
attachTagAutocomplete(taskTagsInput, taskTagsSuggestions);
attachTaskEditTagPicker();
attachFileDropzones();

if (openTaskModalBtn) {
    openTaskModalBtn.addEventListener("click", openTaskModal);
}
document.querySelectorAll("#open-task-modal-header, #open-task-modal-empty").forEach((btn) => {
    btn.addEventListener("click", openTaskModal);
});
taskAddChecklistItemBtn?.addEventListener("click", () => addChecklistInput().focus());
closeTaskModalBtn.addEventListener("click", closeTaskModal);
modalOverlay.addEventListener("click", (event) => {
    if (event.target === modalOverlay && !isMobileViewport()) {
        closeTaskModal();
    }
});
document.querySelector('[data-modal-cancel="task"]')?.addEventListener("click", closeTaskModal);

openProjectModalBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    openProjectModal();
});
closeProjectModalBtn.addEventListener("click", closeProjectModal);
projectModalOverlay.addEventListener("click", (event) => {
    if (event.target === projectModalOverlay) {
        closeProjectModal();
    }
});

closeBackupModalBtn.addEventListener("click", closeBackupModal);
backupModalOverlay.addEventListener("click", (event) => {
    if (event.target === backupModalOverlay) {
        closeBackupModal();
    }
});

if (openSettingsModalBtn) {
    openSettingsModalBtn.addEventListener("click", openSettingsModal);
}
closeSettingsModalBtn.addEventListener("click", closeSettingsModal);
settingsModalOverlay.addEventListener("click", (event) => {
    if (event.target === settingsModalOverlay) {
        closeSettingsModal();
    }
});
if (settingsOpenBackupBtn) {
    settingsOpenBackupBtn.addEventListener("click", () => {
        closeSettingsModal();
        openBackupModal();
    });
}

editProjectButtons.forEach((button) => {
    button.addEventListener("click", () => {
        openProjectEditModal(
            button.dataset.projectId,
            button.dataset.projectName,
            button.dataset.projectIcon
        );
    });
});
closeProjectEditModalBtn.addEventListener("click", closeProjectEditModal);
projectDeleteForm.dataset.confirm = "Удалить проект? Задачи останутся без проекта.";
projectEditModalOverlay.addEventListener("click", (event) => {
    if (event.target === projectEditModalOverlay) {
        closeProjectEditModal();
    }
});

openTagModalBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    openTagModal();
});
closeTagModalBtn.addEventListener("click", closeTagModal);
tagModalOverlay.addEventListener("click", (event) => {
    if (event.target === tagModalOverlay) {
        closeTagModal();
    }
});

editTagButtons.forEach((button) => {
    button.addEventListener("click", () => {
        openTagEditModal(button.dataset.tagId, button.dataset.tagName, button.dataset.tagColor);
    });
});
closeTagEditModalBtn.addEventListener("click", closeTagEditModal);
tagEditModalOverlay.addEventListener("click", (event) => {
    if (event.target === tagEditModalOverlay) {
        closeTagEditModal();
    }
});

taskEditForm.addEventListener("submit", (event) => {
    event.preventDefault();
});
taskEditDescriptionInput.addEventListener("input", resizeTaskEditDescriptionInput);
taskEditAddChecklistItemBtn?.addEventListener("click", () => addEditChecklistInput("", "", false).focus());
taskEditSaveBtn.addEventListener("click", async () => {
    addTaskEditTagFromSearch();
    taskEditSaveBtn.disabled = true;
    try {
        const response = await fetch(taskEditForm.action, {
            method: "POST",
            body: new FormData(taskEditForm),
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": CSRF_TOKEN
            }
        });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            alert(payload.error || "Не удалось сохранить задачу.");
            return;
        }
        updateTaskCard(payload.task);
        closeTaskEditModal();
        showToast("Задача сохранена");
    } catch (error) {
        alert("Ошибка сети при сохранении задачи.");
    } finally {
        taskEditSaveBtn.disabled = false;
    }
});
taskItems.forEach((taskItem) => {
    taskItem.addEventListener("dblclick", (event) => {
        if (event.target.closest("button, a, input, textarea, select, form, label")) {
            return;
        }
        openTaskEditModal(taskItem.dataset.taskId);
    });
});
closeTaskEditModalBtn.addEventListener("click", closeTaskEditModal);
taskEditModalOverlay.addEventListener("click", (event) => {
    if (event.target === taskEditModalOverlay && !isMobileViewport()) {
        closeTaskEditModal();
    }
});
document.querySelector('[data-modal-cancel="task-edit"]')?.addEventListener("click", closeTaskEditModal);
