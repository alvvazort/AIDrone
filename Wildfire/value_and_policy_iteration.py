import mdptoolbox.mdp as mdp
import numpy

def value_iteration(transiciones_sistema, recompensas_sistema, estados, acciones):
    wild_fire_VI = mdp.ValueIteration(
        transitions=transiciones_sistema,
        reward=recompensas_sistema,
        discount=0.9,
        epsilon=0.1
    )
    wild_fire_VI.setVerbose()
    wild_fire_VI.run()

    wild_fire_VI.policy

    for estado, i in zip(estados, wild_fire_VI.policy):
        print(f'En el estado {estado} ejecuta la acción {acciones[i]}')
    return wild_fire_VI.policy


def policy_iteration(transiciones_sistema, recompensas_sistema, estados, acciones):
    wild_fire_PI = mdp.PolicyIteration(
        transitions=transiciones_sistema,
        reward=recompensas_sistema,
        discount=0.9,
        policy0=numpy.array([1, 1, 1, 1, 1, 1, 1, 1, 1,0])  # La política inicial es esperar en cada estado
    )

    wild_fire_PI.setVerbose()
    wild_fire_PI.run()

    print()
    for estado, i in zip(estados, wild_fire_PI.policy):
        print(f'En el estado {estado} ejecuta la acción {acciones[i]}')
    return wild_fire_PI.policy

def run():

    
    estados = ['F','M','A2','A3','A4','A5','PC2', 'PC3', 'PC4', 'PC5'] 

    acciones = ['actua','viaja']

    recompensas_estados = numpy.array([0, -5000, 0, 0, 0, 0, 0, 0, 0, 0]) 

    print("Recompensas de estados:")
    print(recompensas_estados)

    
    transición_actua = numpy.array([[1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                    [0, 0.2, 0.8, 0, 0, 0, 0, 0, 0, 0],
                                    [0, 0.05, 0.25, 0.7, 0, 0, 0, 0, 0, 0],
                                    [0, 0, 0.1, 0.2, 0.7, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0.1, 0.2, 0.7, 0, 0, 0,0],
                                    [0, 0, 0, 0, 0, 0, 0.2, 0.8, 0, 0],
                                    [0, 0, 0, 0, 0, 0, 0, 0.2, 0.8, 0],
                                    [0, 0, 0, 0, 0, 0, 0, 0, 0.2, 0.8],
                                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]])

    
    print("\nTransición actua:")
    print(transición_actua)

    # ['F','M','A2','A3','A4','A5','PC2', 'PC3', 'PC4', 'PC5'] 
    coste_actua = numpy.array([0, 0, -400, -400, -400, -400, 0, 0, 0, 1000])
    
    transición_viaja = numpy.array([[1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                    [0, 0.2, 0, 0, 0, 0, 0.8, 0, 0, 0],
                                    [0, 0.1, 0, 0, 0, 0, 0.3, 0.6, 0, 0],
                                    [0, 0,	0, 0, 0, 0, 0.1, 0.3, 0.6, 0],
                                    [0, 0, 0, 0, 0, 0, 0, 0.1, 0.3, 0.6],
                                    [0, 0.2, 0.8, 0, 0, 0, 0, 0, 0, 0],
                                    [0, 0.1, 0.3, 0.6, 0, 0, 0, 0, 0, 0],
                                    [0, 0,	0.1, 0.3, 0.6, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0.1, 0.3, 0.6, 0, 0, 0, 0]])
    print("\nTransición viaja:")
                 
    print(transición_viaja)

    # ['F','M','A2','A3','A4','A5','PC2', 'PC3', 'PC4', 'PC5'] 
    coste_viaja = numpy.array([numpy.inf, numpy.inf, 20, 200, 200, 200, 20, 20, 20, 20])

    transiciones_sistema = numpy.array([transición_actua,
                                    transición_viaja])


    # Transformamos el vector de recompensas en una matriz 10x1
    matriz_recompensas = recompensas_estados.reshape(10, 1)

    # Creamos una matriz donde cada columna es el vector de costes de una acción
    matriz_costes = numpy.column_stack([coste_actua,
                                        coste_viaja])

    recompensas_sistema = matriz_recompensas - matriz_costes  
    print("\nRecompensas del sistema: ")
    print(recompensas_sistema)

    policy = value_iteration(transiciones_sistema, recompensas_sistema, estados, acciones)
    #policy = policy_iteration(transiciones_sistema, recompensas_sistema, estados, acciones)
    


if __name__ == "__main__":
    run()


    # Parking de cursores
    # |---------------------|
            
    # |---------------------|