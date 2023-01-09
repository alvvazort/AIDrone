import mdptoolbox.mdp as mdp
import numpy


def run():
    
    estados = ['M','PC2','PC3','PC4','PC5','A2', 'A3', 'A4', 'A5'] 

    acciones = ['actua','viaja']

    recompensas_estados = numpy.array([-1000, 0, 0, 0, -100, 100, 100, 100, 100]) 

    print("Recompensas de estados:")
    print(recompensas_estados)

    transición_actua = numpy.array([[1,0,0,0,0,0,0,0,0],
                                    [0.15, 0.85, 0, 0, 0, 0, 0, 0, 0],
                                    [0.05, 0.25, 0.7, 0, 0, 0, 0, 0, 0],
                                    [0, 0.1, 0.2, 0.7, 0, 0, 0, 0, 0],
                                    [0, 0, 0.1, 0.2, 0.7, 0, 0, 0,0],
                                    [0, 0, 0, 0, 0, 0.2, 0.8, 0, 0],
                                    [0, 0, 0, 0, 0, 0, 0.2, 0.8, 0],
                                    [0, 0, 0, 0, 0, 0, 0, 0.2, 0.8],
                                    [0, 0, 0, 0, 0, 0, 0, 0, 1]])
    
    print("\nTransición actua:")
    print(transición_actua)

    # ['M','PC2','PC3','PC4','PC5','A2', 'A3', 'A4', 'A5'] 
    coste_actua = numpy.array([numpy.inf, 0, 0, 0, 0, 0, 0, 0, 0])
    
    transición_viaja = numpy.array([[1, 0, 0, 0, 0, 0, 0, 0, 0],
                                    [0.2, 0, 0, 0, 0, 0.8, 0, 0, 0],
                                    [0.1, 0, 0, 0, 0, 0.3, 0.6, 0, 0],
                                    [0,	0, 0, 0, 0, 0.1, 0.3, 0.6, 0],
                                    [0, 0, 0, 0, 0, 0, 0.1, 0.3, 0.6],
                                    [0.2, 0.8, 0, 0, 0, 0, 0, 0, 0],
                                    [0.1, 0.3, 0.6, 0, 0, 0, 0, 0, 0],
                                    [0,	0.1, 0.3, 0.6, 0, 0, 0, 0, 0],
                                    [0, 0, 0.1, 0.3, 0.6, 0, 0, 0, 0]])
    print("\nTransición viaja:")
                 
    print(transición_viaja)

    # ['M','PC2','PC3','PC4','PC5','A2', 'A3', 'A4', 'A5'] 
    coste_viaja = numpy.array([numpy.inf, 0, 0, 0, 0, 0, 0, 0, 0])

    transiciones_sistema = numpy.array([transición_actua,
                                    transición_viaja])


    # Transformamos el vector de recompensas en una matriz 9x1
    matriz_recompensas = recompensas_estados.reshape(9, 1)

    # Creamos una matriz donde cada columna es el vector de costes de una acción
    matriz_costes = numpy.column_stack([coste_actua,
                                        coste_viaja])

    recompensas_sistema = matriz_recompensas - matriz_costes  #9x1 - 9x2
    print("\nRecompensas del sistema: ")
    print(recompensas_sistema)


    wild_fire_VI = mdp.ValueIteration(
    transitions=transiciones_sistema,
    reward=recompensas_sistema,
    discount=0.9,
    epsilon=0.1)

    wild_fire_VI.setVerbose()
    wild_fire_VI.run()

    wild_fire_VI.policy

    for estado, i in zip(estados, wild_fire_VI.policy):
        print(f'En el estado {estado} ejecuta la acción {acciones[i]}')


if __name__ == "__main__":
    run()


    # Parking de cursores
    # |---------------------|
            
    # |---------------------|