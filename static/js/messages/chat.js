document.addEventListener("DOMContentLoaded", function () {
  const bottom = document.getElementById("chat-bottom");
  if (bottom) {
    bottom.scrollIntoView({ behavior: "instant", block: "end" });
  }
});