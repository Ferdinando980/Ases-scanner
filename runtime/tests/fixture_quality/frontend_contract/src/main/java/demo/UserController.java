@Controller class UserController {
    @GetMapping("/api/users") public String users() { return "ok"; }
}
