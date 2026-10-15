package demo;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/")
public class AuthController {
  private final AuthService authService;
  public AuthController(AuthService authService){ this.authService=authService; }
  @PostMapping("/login")
  public String login(){ return authService.login(); }
  @GetMapping("/logout")
  public String logout(){ return authService.logout(); }
}
