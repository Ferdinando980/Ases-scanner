package demo;
public class MazzoFactory {
  public static Object create(String tipo) {
    switch(tipo) {
      case "a": return new MazzoA();
      default: return new MazzoB();
    }
  }
}
class MazzoA {}
class MazzoB {}
