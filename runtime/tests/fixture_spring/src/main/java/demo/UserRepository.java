package demo;
import org.springframework.stereotype.Repository;
@Repository
public class UserRepository {
  public User save(User user) { return user; }
}
