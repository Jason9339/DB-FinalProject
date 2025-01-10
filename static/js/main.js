$(document).ready(function () {
  $(".favorite-toggle").click(function () {
    const movieId = $(this).data("movie-id");
    $.post(`/favorite/${movieId}`, function () {
      alert("Favorite list updated!");
      location.reload();
    }).fail(function () {
      alert("Failed to update favorites. Please try again.");
    });
  });
});
