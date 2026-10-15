package demo;
import org.springframework.stereotype.Service;
@Service
public class UserService {
  private final UserRepository repository;
  public UserService(UserRepository repository) { this.repository = repository; }
  public User create(String email) { return repository.save(new User(email)); }
}
