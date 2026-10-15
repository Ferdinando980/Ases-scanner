package demo;
import org.junit.jupiter.api.Test;
public class AuthServiceTest {
  private AuthService authService;
  @Test
  public void login_success() { authService.login(); }
}
