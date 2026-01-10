psql:
	docker-compose --file ./docker-compose-postgres.yml up -d --remove-orphans
build: 
	docker-compose --file ./docker-compose.yml up -d --build
	watch make show
show:
	docker ps -a --filter "name=teamlead"
clean:
	docker-compose down