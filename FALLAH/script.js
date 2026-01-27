function toggleMenu() {
  const nav = document.getElementById("nav");
  nav.style.display = nav.style.display === "flex" ? "none" : "flex";
}

// Optional: Alert when contact form is submitted
document.getElementById("contactForm")?.addEventListener("submit", function(e) {
  e.preventDefault();
  alert("Message sent successfully. We will contact you soon.");
});