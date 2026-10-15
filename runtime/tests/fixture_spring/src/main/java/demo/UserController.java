package demo;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/users")
public class UserController {
  private final UserService userService;
  public UserController(UserService userService) { this.userService = userService; }
  @PostMapping
  public User create(String email) { return userService.create(email); }
}
