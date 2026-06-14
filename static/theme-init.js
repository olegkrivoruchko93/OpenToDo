(function () {
    var k = "opentodo-theme";
    var v = localStorage.getItem(k);
    var themes = ["default", "warm", "dark", "ocean", "forest", "violet", "autumn", "sky", "gravel"];
    if (themes.indexOf(v) === -1) v = "default";
    document.documentElement.setAttribute("data-theme", v);
})();
