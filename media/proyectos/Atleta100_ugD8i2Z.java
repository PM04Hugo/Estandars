import jakarta.ws.rs.client.*;
import jakarta.ws.rs.core.*;
import java.net.URI;
import java.util.Random;

public class Atleta100 extends Thread 
{
    private int dorsal;
	private Disparo pistola;

	public Atleta100(int dorsal, Disparo pistola) {
		this.dorsal=dorsal;
		this.pistola=pistola;
	}
    public synchronized void run()
	{
        long fin;
        long inicio;
        int tiempo;
        synchronized(pistola) {
            try {
                pistola.wait();
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        inicio = System.currentTimeMillis();    
        try {
            tiempo = 9000+ (int)(Math.random() *2000);
            Thread.sleep(tiempo);
        }catch (InterruptedException e)
        {
            e.printStackTrace();
        }    
        fin = System.currentTimeMillis()-inicio;

	}
    public String tiempo_inicio()
    {
        return "Atleta "+dorsal+" inicio en: "+inicio;

    }
    public String tiempo_fin()
    {
        return "Atleta "+dorsal+" termino con un tiempo de: "+fin;

    }
    


}