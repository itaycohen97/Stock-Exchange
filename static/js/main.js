const delay = (ms) => new Promise((res) => setTimeout(res, ms));
function decide_width() {
  if (425 > window.screen.width) return "100%";
  else return "300px";
}
function toggleNav() {
  if (document.getElementById("Sidenav").clientWidth == "0")
    document.getElementById("Sidenav").style.width = decide_width();
  else document.getElementById("Sidenav").style.width = "0";
}
function toggleUser() {
  const usermenu = document.getElementById("usermenu");
  if (usermenu.style.display == "none") usermenu.style.display = "block";
  else usermenu.style.display = "none";
}

document.getElementById("usermenutoggle").addEventListener("click", toggleUser);
