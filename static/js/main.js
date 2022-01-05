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
async function skip_song() {
  const token = document.getElementById("token").innerText;
  const response = await fetch("https://api.spotify.com/v1/me/player/next", {
    method: "POST", // *GET, POST, PUT, DELETE, etc.
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: "Bearer " + token,
    },
  });
  return token;
}

async function get_song() {
  token = await skip_song();
  delay(500);
  const response = await fetch(
    "https://api.spotify.com/v1/me/player/currently-playing?market=IL",
    {
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
    }
  ).then((res) => {
    console.log(res);
    const data = res.json();
    document.getElementById("songname").innerHTML =
      "<b>Now Playing:</b><br>" +
      data.item.name +
      "<br>" +
      data.item.artists[0]["name"];
    return;
  });
  return response;
}

document.getElementById("usermenutoggle").addEventListener("click", toggleUser);
document.getElementById("skip_btn").addEventListener("click", get_song);
